"""
Demostración de análisis en vivo sobre la cámara IP.

Detecta el estado de la puerta con YOLO dentro de las ROIs definidas y
cronometra cuánto tiempo permanece abierta. No depende del backend Django:
los eventos se imprimen y se guardan en alertas/demo_eventos.json.

El motor de detección vive en app/analisis.py, compartido con el worker de
producción (app/analisis_en_vivo.py). Aquí queda solo la CLI de la demo.

Uso:
    python -m app.demo_analisis                 # ventana en vivo
    python -m app.demo_analisis --sin-ventana   # solo consola (para servidor)
    python -m app.demo_analisis --segundos 30   # corta a los 30s
    python -m app.demo_analisis --guardar demo.mp4

Controles: q = salir
"""
import argparse
import json
import os
import sys
import time

import cv2
from ultralytics import YOLO

from app.analisis import (
    ALTO_VENTANA,
    ANCHO_VENTANA,
    BASE_DIR,
    CLASES_ABIERTA,
    CLASES_ABIERTA_ESTRICTO,
    FPS_ANALISIS_POR_DEFECTO,
    IMGSZ_POR_DEFECTO,
    RUTA_MODELO,
    analizar_frame,
    crear_estados,
    dibujar,
)
from app.config import obtener_origen_video, ocultar_password, USAR_CAMARA_IP
from app.lector_camara import LectorCamara
from app.roi_config import cargar_rois

RUTA_EVENTOS = os.path.join(BASE_DIR, "alertas", "demo_eventos.json")


def main():
    parser = argparse.ArgumentParser(description="Demo de analisis de puertas en vivo")
    parser.add_argument("--sin-ventana", action="store_true", help="No abrir ventana (modo servidor)")
    parser.add_argument("--segundos", type=float, default=0, help="Detener tras N segundos")
    parser.add_argument("--guardar", metavar="ARCHIVO", help="Grabar el analisis a un mp4")
    parser.add_argument("--imgsz", type=int, default=IMGSZ_POR_DEFECTO,
                        help=f"Resolucion de inferencia (def. {IMGSZ_POR_DEFECTO}; mas alto = mas lento)")
    parser.add_argument("--fps-analisis", type=float, default=FPS_ANALISIS_POR_DEFECTO,
                        help=f"Limite de frames analizados por segundo (def. {FPS_ANALISIS_POR_DEFECTO})")
    parser.add_argument("--estricto", action="store_true",
                        help="Contar solo 'puerta_abierta', ignorando 'puerta_medio_abierta'")
    args = parser.parse_args()

    clases_abierta = CLASES_ABIERTA_ESTRICTO if args.estricto else CLASES_ABIERTA

    origen = obtener_origen_video()
    print(f"[DEMO] Origen: {ocultar_password(origen)}")
    print(f"[DEMO] Modo: {'camara IP en vivo' if USAR_CAMARA_IP else 'video local'}")
    print(f"[DEMO] Cuenta como abierta: {', '.join(sorted(clases_abierta))}")

    if not os.path.exists(RUTA_MODELO):
        print(f"[ERROR] No se encontro el modelo en {RUTA_MODELO}")
        return 1

    print("[DEMO] Cargando modelo YOLO...")
    modelo = YOLO(RUTA_MODELO)

    zonas = cargar_rois(origen)
    if zonas:
        print(f"[DEMO] {len(zonas)} zona(s) cargada(s): {', '.join(z.nombre for z in zonas)}")
    else:
        print("[AVISO] No hay ROIs para este origen. Analizando la escena completa.")
        print("        Define las zonas con: python vision_worker/scripts/definir_roi.py")

    # Sin publicador: la demo no escribe nada en la base de datos.
    estados = crear_estados(zonas)

    print("[DEMO] Conectando...\n")
    lector = LectorCamara(origen).iniciar()

    grabador = None
    inicio = time.time()
    analizados = 0
    fps = 0.0
    intervalo_min = 1.0 / args.fps_analisis if args.fps_analisis > 0 else 0.0
    proximo_analisis = 0.0

    try:
        while lector.activo:
            nuevo, frame = lector.leer()
            if not nuevo or time.time() < proximo_analisis:
                time.sleep(0.005)
                continue

            proximo_analisis = time.time() + intervalo_min
            dibujables = analizar_frame(modelo, frame, zonas, estados,
                                        imgsz=args.imgsz, clases_abierta=clases_abierta)
            analizados += 1
            fps = analizados / max(time.time() - inicio, 0.001)

            if not args.sin_ventana or args.guardar:
                vista = dibujar(frame, zonas, estados, dibujables, fps,
                                lector.frames_perdidos, clases_abierta)

                if args.guardar:
                    if grabador is None:
                        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                        grabador = cv2.VideoWriter(args.guardar, fourcc, 10,
                                                   (ANCHO_VENTANA, ALTO_VENTANA))
                    grabador.write(vista)

                if not args.sin_ventana:
                    cv2.imshow("Demo - Control de puertas", vista)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break

            if args.segundos and (time.time() - inicio) >= args.segundos:
                break

    except KeyboardInterrupt:
        print("\n[DEMO] Interrumpido por el usuario.")
    finally:
        lector.detener()
        if grabador:
            grabador.release()
            print(f"[DEMO] Video guardado en {args.guardar}")
        cv2.destroyAllWindows()

    resumen(estados, analizados, time.time() - inicio, lector)
    return 0


def resumen(estados, analizados, transcurrido, lector):
    print("\n" + "=" * 60)
    print("RESUMEN DE LA SESION")
    print("=" * 60)
    print(f"  Duracion            : {transcurrido:.1f}s")
    print(f"  Frames analizados   : {analizados} ({analizados / max(transcurrido, 0.1):.1f} fps)")
    print(f"  Frames descartados  : {lector.frames_perdidos} (llegaron mientras YOLO procesaba)")
    print(f"  Reconexiones        : {lector.desconexiones}")

    todos = []
    for estado in estados.values():
        eventos = list(estado.eventos)
        # Una apertura aun en curso al terminar la sesion tambien cuenta
        en_curso = estado.evento_en_curso()
        if en_curso:
            eventos.append(en_curso)
        todos.extend(eventos)

        print(f"\n  {estado.nombre}: {len(eventos)} evento(s), estado final = {estado.estado}")
        for ev in eventos:
            marca = "ALERTA" if ev["supero_umbral"] else "ok"
            cierre = ev["cierre"][11:19] if ev["cierre"] else "en curso"
            print(f"    {ev['apertura'][11:19]} -> {cierre}  ({ev['duracion_segundos']}s) [{marca}]")

    if todos:
        os.makedirs(os.path.dirname(RUTA_EVENTOS), exist_ok=True)
        with open(RUTA_EVENTOS, "w", encoding="utf-8") as f:
            json.dump(todos, f, indent=2, ensure_ascii=False)
        print("\n  Eventos guardados en alertas/demo_eventos.json")
    print("=" * 60)


if __name__ == "__main__":
    sys.exit(main())
