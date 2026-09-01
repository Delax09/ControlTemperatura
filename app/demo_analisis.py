"""
Demostración de análisis en vivo sobre la cámara IP.

Detecta el estado de la puerta con YOLO dentro de las ROIs definidas y
cronometra cuánto tiempo permanece abierta. No depende del backend Django:
los eventos se imprimen y se guardan en alertas/demo_eventos.json.

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
from datetime import datetime

import cv2
from ultralytics import YOLO

from app.config import obtener_origen_video, ocultar_password, USAR_CAMARA_IP
from app.lector_camara import LectorCamara
from app.roi_config import cargar_rois

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUTA_MODELO = os.path.join(BASE_DIR, "runs/detect/runs/detect/modelo_puerta_robusto/weights/best.pt")
RUTA_EVENTOS = os.path.join(BASE_DIR, "alertas", "demo_eventos.json")

UMBRAL_CONFIANZA = 0.55
SEGUNDOS_CONFIRMACION = 1.5  # cuánto debe sostenerse un cambio para darlo por cierto
SOLAPAMIENTO_MINIMO = 0.35   # cuánto de la caja debe caer dentro de la ROI
SEGUNDOS_ALERTA = 30         # puerta abierta más de esto = alerta
# El modelo actual confunde la cortina de PVC bajada con "puerta_medio_abierta"
# (0.96 de confianza sobre una puerta cerrada en esta camara). Con --estricto
# solo cuenta "puerta_abierta", que evita el falso positivo mientras no se
# reentrene con frames de esta camara.
CLASES_ABIERTA = {"puerta_abierta", "puerta_medio_abierta"}
CLASES_ABIERTA_ESTRICTO = {"puerta_abierta"}

# YOLO corre en CPU: 1080p tarda ~550 ms por frame y 640 px ~210 ms.
# Una puerta es un objeto grande, no necesita resolución completa.
IMGSZ_POR_DEFECTO = 640
FPS_ANALISIS_POR_DEFECTO = 4.0   # límite de ritmo, para no saturar la CPU

ANCHO_VENTANA, ALTO_VENTANA = 1024, 576
VERDE, ROJO, AMARILLO, BLANCO = (0, 200, 0), (0, 0, 255), (0, 200, 255), (255, 255, 255)


class EstadoPuerta:
    """
    Máquina de estados de una puerta con anti-rebote.

    Un solo frame detectado no cambia el estado: la condición debe sostenerse
    SEGUNDOS_CONFIRMACION. Sin esto, una persona pasando delante de la puerta
    genera aperturas y cierres falsos.

    El anti-rebote se mide en segundos y no en frames a propósito: el ritmo de
    análisis varía con la carga de la CPU, y contar frames haría que el retardo
    de confirmación cambiara solo porque la máquina va más lenta.
    """

    def __init__(self, nombre):
        self.nombre = nombre
        self.estado = "cerrada"
        self.confianza = 0.0
        self.abierta_desde = None
        self.alerta_emitida = False
        self._cambio_desde = None   # instante en que la condición contraria empezó
        self.eventos = []

    @property
    def segundos_abierta(self):
        return (datetime.now() - self.abierta_desde).total_seconds() if self.abierta_desde else 0.0

    @property
    def en_alerta(self):
        return self.estado == "abierta" and self.segundos_abierta >= SEGUNDOS_ALERTA

    def actualizar(self, detectada, confianza):
        self.confianza = confianza if detectada else 0.0
        ahora = datetime.now()
        contradice = detectada if self.estado == "cerrada" else not detectada

        if not contradice:
            self._cambio_desde = None
        else:
            if self._cambio_desde is None:
                self._cambio_desde = ahora

            elif (ahora - self._cambio_desde).total_seconds() >= SEGUNDOS_CONFIRMACION:
                # El evento se fecha en el instante en que empezó a verse, no
                # cuando se confirmó: si no, cada duración perdería 1.5s.
                inicio_real = self._cambio_desde
                self._cambio_desde = None

                if self.estado == "cerrada":
                    self.estado = "abierta"
                    self.abierta_desde = inicio_real
                    self.alerta_emitida = False
                    print(f"  [{hora()}] {self.nombre}: APERTURA detectada (conf {confianza:.2f})")
                else:
                    duracion = (inicio_real - self.abierta_desde).total_seconds()
                    self.eventos.append({
                        "puerta": self.nombre,
                        "apertura": self.abierta_desde.isoformat(),
                        "cierre": inicio_real.isoformat(),
                        "duracion_segundos": round(duracion, 1),
                        "supero_umbral": duracion >= SEGUNDOS_ALERTA,
                    })
                    self.estado = "cerrada"
                    self.abierta_desde = None
                    self.alerta_emitida = False
                    print(f"  [{hora()}] {self.nombre}: CIERRE tras {duracion:.1f}s")

        # Alerta de puerta abierta demasiado tiempo (una sola vez por apertura)
        if self.en_alerta and not self.alerta_emitida:
            self.alerta_emitida = True
            print(f"\n\033[91m  [ALERTA] {self.nombre} lleva {self.segundos_abierta:.0f}s abierta\033[0m\n")
            try:
                import winsound
                winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
            except Exception:
                pass


def hora():
    return datetime.now().strftime("%H:%M:%S")


def analizar_frame(modelo, frame, zonas, estados, imgsz=IMGSZ_POR_DEFECTO,
                    clases_abierta=CLASES_ABIERTA):
    """
    Corre YOLO sobre el frame y reparte las detecciones entre las zonas.
    Retorna las cajas dibujables [(caja, clase, confianza, nombre_zona)].
    """
    resultados = modelo(frame, imgsz=imgsz, conf=UMBRAL_CONFIANZA, verbose=False)

    detecciones = []
    for r in resultados:
        for box in r.boxes:
            nombre_clase = modelo.names[int(box.cls[0])]
            detecciones.append((box.xyxy[0].tolist(), nombre_clase, float(box.conf[0])))

    # Confianza máxima de "abierta" por zona
    confianza_por_zona = {nombre: 0.0 for nombre in estados}
    dibujables = []

    for caja, nombre_clase, conf in detecciones:
        if zonas:
            zona_asignada = None
            mejor = SOLAPAMIENTO_MINIMO
            for zona in zonas:
                solape = zona.fraccion_dentro(caja, frame.shape)
                if solape >= mejor:
                    mejor, zona_asignada = solape, zona.nombre
            if zona_asignada is None:
                continue   # detección fuera de toda ROI: se ignora
        else:
            zona_asignada = "Escena completa"

        if nombre_clase in clases_abierta:
            confianza_por_zona[zona_asignada] = max(confianza_por_zona[zona_asignada], conf)

        dibujables.append((caja, nombre_clase, conf, zona_asignada))

    for nombre, estado in estados.items():
        estado.actualizar(confianza_por_zona[nombre] > 0, confianza_por_zona[nombre])

    return dibujables


def dibujar(frame, zonas, estados, dibujables, fps, perdidos, clases_abierta=CLASES_ABIERTA):
    """Arma el frame de visualización a escala reducida."""
    forma_original = frame.shape
    vista = cv2.resize(frame, (ANCHO_VENTANA, ALTO_VENTANA))
    ex = ANCHO_VENTANA / forma_original[1]
    ey = ALTO_VENTANA / forma_original[0]

    for zona in zonas:
        activa = estados[zona.nombre].estado == "abierta"
        zona.dibujar(vista, escala_x=ex, escala_y=ey, activa=activa, forma_original=forma_original)

    for caja, nombre_clase, conf, _ in dibujables:
        x1, y1 = int(caja[0] * ex), int(caja[1] * ey)
        x2, y2 = int(caja[2] * ex), int(caja[3] * ey)
        color = ROJO if nombre_clase in clases_abierta else VERDE
        cv2.rectangle(vista, (x1, y1), (x2, y2), color, 2)
        cv2.putText(vista, f"{nombre_clase} {conf:.2f}", (x1, max(14, y1 - 6)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

    # Panel de estado
    cv2.rectangle(vista, (0, 0), (ANCHO_VENTANA, 30 + 26 * len(estados)), (0, 0, 0), -1)
    cv2.putText(vista, f"{hora()}  |  {fps:.1f} fps analisis  |  {perdidos} frames descartados",
                (12, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, BLANCO, 1)

    y = 46
    for estado in estados.values():
        if estado.estado == "abierta":
            color = ROJO if estado.en_alerta else AMARILLO
            texto = f"{estado.nombre}: ABIERTA  {estado.segundos_abierta:5.1f}s  (conf {estado.confianza:.2f})"
        else:
            color, texto = VERDE, f"{estado.nombre}: cerrada"
        cv2.putText(vista, texto, (12, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        y += 26

    return vista


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
        estados = {z.nombre: EstadoPuerta(z.nombre) for z in zonas}
    else:
        print("[AVISO] No hay ROIs para este origen. Analizando la escena completa.")
        print("        Define las zonas con: python vision_worker/scripts/definir_roi.py")
        estados = {"Escena completa": EstadoPuerta("Escena completa")}

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
        if estado.abierta_desde:
            eventos.append({
                "puerta": estado.nombre,
                "apertura": estado.abierta_desde.isoformat(),
                "cierre": None,
                "duracion_segundos": round(estado.segundos_abierta, 1),
                "supero_umbral": estado.segundos_abierta >= SEGUNDOS_ALERTA,
            })
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
