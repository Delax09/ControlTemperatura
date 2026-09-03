"""
Worker de analisis en vivo. Es lo que arranca el boton "Analizar video" del
muro de control.

Toma el video en tiempo real de la camara (o el video local, segun
USAR_CAMARA_IP del .env), corre el modelo sobre las ROIs definidas y registra
cada apertura y cierre en la API. A diferencia de app/demo_analisis.py, este
esta pensado para correr desatendido: sin ventana, publicando los datos y
reportando su estado en un archivo que el backend consulta (ver
app/estado_analisis.py).

Se detiene por archivo y no matando el proceso a proposito: matarlo dejaria la
apertura en curso sin hora de cierre en la base.

Uso:
    python -m app.analisis_en_vivo --puerta PSP-01
    python -m app.analisis_en_vivo --puerta PSP-01 --ventana      # ver el video
    python -m app.analisis_en_vivo --puerta PSP-01 --segundos 60  # corta a los 60s
    python -m app.analisis_en_vivo --puerta PSP-01 --estricto     # ignora "medio_abierta"
    python -m app.analisis_en_vivo --puerta PSP-01 --sin-api      # no escribe en la base
"""
import argparse
import os
import sys
import time
import traceback
from datetime import datetime

import cv2

from app.analisis import (
    CLASES_ABIERTA,
    CLASES_ABIERTA_ESTRICTO,
    FPS_ANALISIS_POR_DEFECTO,
    IMGSZ_POR_DEFECTO,
    RUTA_MODELO,
    SEGUNDOS_ALERTA,
    analizar_frame,
    cargar_modelo,
    crear_estados,
    dibujar,
    hora,
)
from app.config import USAR_CAMARA_IP, obtener_origen_video, ocultar_password
from app.estado_analisis import (
    SEGUNDOS_LATIDO,
    ArchivoEstado,
    detencion_pedida,
    limpiar_detencion,
    referencia_detencion,
)
from app.lector_camara import LectorCamara
from app.publicador_eventos import PublicadorEventos
from app.roi_config import cargar_rois


def resumen_zonas(estados):
    """Estado de cada zona, en la forma que consume el muro."""
    return [
        {
            "nombre": e.nombre,
            "estado": e.estado,
            "segundos_abierta": round(e.segundos_abierta, 1),
            "confianza": round(e.confianza, 2),
            "en_alerta": e.en_alerta,
        }
        for e in estados.values()
    ]


def main():
    parser = argparse.ArgumentParser(description="Analisis en vivo de una puerta, con registro en la API")
    parser.add_argument("--puerta", required=True,
                        help="Id de la puerta en el muro (ej. PSP-01). Identifica esta sesion de analisis")
    parser.add_argument("--ventana", action="store_true",
                        help="Abrir el visor con el video anotado (en la maquina del servidor). "
                             "Cerrarlo no detiene el analisis")
    parser.add_argument("--segundos", type=float, default=0, help="Detener tras N segundos (0 = sin limite)")
    parser.add_argument("--imgsz", type=int, default=IMGSZ_POR_DEFECTO,
                        help=f"Resolucion de inferencia (def. {IMGSZ_POR_DEFECTO}; mas alto = mas lento)")
    parser.add_argument("--fps-analisis", type=float, default=FPS_ANALISIS_POR_DEFECTO,
                        help=f"Limite de frames analizados por segundo (def. {FPS_ANALISIS_POR_DEFECTO})")
    parser.add_argument("--segundos-alerta", type=float, default=SEGUNDOS_ALERTA,
                        help=f"Segundos abierta para considerarlo alerta (def. {SEGUNDOS_ALERTA})")
    parser.add_argument("--estricto", action="store_true",
                        help="Contar solo 'puerta_abierta', ignorando 'puerta_medio_abierta'")
    parser.add_argument("--sin-api", action="store_true",
                        help="No escribir en la base: los eventos van solo al respaldo local")
    args = parser.parse_args()

    clases_abierta = CLASES_ABIERTA_ESTRICTO if args.estricto else CLASES_ABIERTA
    origen = obtener_origen_video()
    origen_visible = ocultar_password(str(origen))

    print("=" * 62)
    print(f"[VIVO] Puerta : {args.puerta}")
    print(f"[VIVO] Origen : {origen_visible}")
    print(f"[VIVO] Modo   : {'camara IP en vivo' if USAR_CAMARA_IP else 'video local'}")
    print(f"[VIVO] Abierta: {', '.join(sorted(clases_abierta))}")
    print("=" * 62)

    if not os.path.exists(RUTA_MODELO):
        print(f"[ERROR] No se encontro el modelo en {RUTA_MODELO}")
        return 1

    # Se toma antes de escribir el estado: a partir de aqui se sabe cuales
    # senales de detencion son de esta sesion y cuales sobraron de una anterior.
    # Se hace asi y no borrando la senal al arrancar porque, con lo que tarda en
    # cargar el modelo, el operador puede pulsar "Detener" antes de que el
    # analisis empiece y ese pedido no se puede perder.
    referencia = referencia_detencion(args.puerta)

    publicador = PublicadorEventos(publicar=not args.sin_api)
    if args.sin_api:
        print("[VIVO] --sin-api: los eventos no entran a la base, solo al respaldo local.")
    elif not publicador.disponible():
        print(f"[AVISO] La API no responde en {publicador.url_eventos}.")
        print("        El analisis igual corre: los eventos quedan en")
        print("        alertas/registro_tiempos_puerta.json para cargarlos despues.")

    zonas = cargar_rois(origen)
    if zonas:
        print(f"[VIVO] {len(zonas)} zona(s): {', '.join(z.nombre for z in zonas)}")
    else:
        print("[AVISO] No hay ROIs para este origen: se analiza la escena completa.")
        print("        Definelas con el boton 'Definir ROI' del muro.")

    estados = crear_estados(zonas, publicador, args.segundos_alerta)
    archivo_estado = ArchivoEstado(args.puerta, origen_visible, USAR_CAMARA_IP, os.getpid())
    archivo_estado.escribir("iniciando", resumen_zonas(estados), mensaje="Cargando el modelo")

    print("[VIVO] Cargando modelo YOLO...")
    try:
        modelo = cargar_modelo(RUTA_MODELO, "VIVO")
    except FileNotFoundError as error:
        print(f"[ERROR] {error}")
        archivo_estado.escribir("error", resumen_zonas(estados), mensaje=str(error))
        limpiar_detencion(args.puerta)
        return 1

    archivo_estado.escribir("iniciando", resumen_zonas(estados), mensaje="Conectando a la camara")
    print("[VIVO] Conectando a la camara...\n")
    try:
        lector = LectorCamara(origen).iniciar()
    except Exception as error:
        print(f"[ERROR] {error}")
        archivo_estado.escribir("error", resumen_zonas(estados), mensaje=str(error))
        limpiar_detencion(args.puerta)
        return 1

    inicio = time.time()
    analizados = 0
    fps = 0.0
    intervalo_min = 1.0 / args.fps_analisis if args.fps_analisis > 0 else 0.0
    proximo_analisis = 0.0
    proximo_latido = 0.0
    motivo = "Se termino el video de origen"
    fallo = None
    titulo_visor = f"Analisis en vivo - {args.puerta}"
    visor_abierto = args.ventana

    def latir(estado="corriendo", mensaje=""):
        nonlocal proximo_latido
        proximo_latido = time.time() + SEGUNDOS_LATIDO
        archivo_estado.escribir(
            estado, resumen_zonas(estados),
            registrados=publicador.registrados,
            sin_enviar=publicador.fallidos,
            fps=fps,
            reconexiones=lector.desconexiones,
            mensaje=mensaje,
            ventana=visor_abierto,
        )

    try:
        while lector.activo:
            if detencion_pedida(args.puerta, referencia):
                motivo = "Detenido desde el muro"
                print(f"\n[VIVO] {motivo}.")
                break

            if args.segundos and (time.time() - inicio) >= args.segundos:
                motivo = f"Limite de {args.segundos:.0f}s alcanzado"
                break

            nuevo, frame = lector.leer()

            # El latido va antes del filtro de frames: si el stream se corta,
            # el muro tiene que seguir viendo un worker vivo reconectando, no
            # uno caido.
            if time.time() >= proximo_latido:
                latir()

            if not nuevo or time.time() < proximo_analisis:
                time.sleep(0.005)
                continue

            proximo_analisis = time.time() + intervalo_min
            dibujables = analizar_frame(modelo, frame, zonas, estados,
                                        imgsz=args.imgsz, clases_abierta=clases_abierta)
            analizados += 1
            fps = analizados / max(time.time() - inicio, 0.001)

            if visor_abierto:
                visor_abierto = mostrar_visor(titulo_visor, frame, zonas, estados,
                                              dibujables, fps, lector, clases_abierta)

    except KeyboardInterrupt:
        motivo = "Interrumpido con Ctrl+C"
        print(f"\n[VIVO] {motivo}.")
    except Exception as error:
        # Se reporta como error y no como final normal: si no, el muro diria que
        # el analisis termino tranquilo y nadie se enteraria de la caida.
        fallo = f"{type(error).__name__}: {error}"
        motivo = f"Cortado por un error: {fallo}"
        print(f"\n[ERROR] {motivo}")
        traceback.print_exc()
    finally:
        cerrar_aperturas_pendientes(estados)
        lector.detener()
        cerrar_visor(titulo_visor)
        archivo_estado.escribir(
            "error" if fallo else "detenido", resumen_zonas(estados),
            registrados=publicador.registrados,
            sin_enviar=publicador.fallidos,
            fps=fps,
            reconexiones=lector.desconexiones,
            mensaje=motivo,
        )
        limpiar_detencion(args.puerta)

    resumen(args.puerta, estados, publicador, analizados, time.time() - inicio, lector, motivo)
    return 0


def mostrar_visor(titulo, frame, zonas, estados, dibujables, fps, lector, clases_abierta):
    """
    Pinta el frame anotado en el visor. Retorna si el visor sigue abierto.

    El visor solo sirve para comprobar a ojo que el modelo esta encuadrando la
    puerta, asi que nada de lo que pase con la ventana puede cortar la toma de
    datos: cerrarla con "q" o con la X la apaga y nada mas, y un fallo de
    highgui tampoco tumba el analisis. La consola sigue registrando y los
    eventos siguen entrando a la base. Para detener el analisis esta el boton
    del muro.
    """
    try:
        vista = dibujar(frame, zonas, estados, dibujables, fps,
                        lector.frames_perdidos, clases_abierta)
        cv2.imshow(titulo, vista)
        pidio_salir = (cv2.waitKey(1) & 0xFF) == ord("q")
        visible = cv2.getWindowProperty(titulo, cv2.WND_PROP_VISIBLE) >= 1
    except cv2.error as error:
        detalle = str(error).splitlines()[-1][:90]
        print(f"  [{hora()}] [AVISO] el visor fallo ({detalle}). Se sigue sin visor.")
        return False

    if not pidio_salir and visible:
        return True

    cerrar_visor(titulo)
    print(f"  [{hora()}] Visor cerrado. El analisis sigue corriendo.")
    return False


def cerrar_visor(titulo):
    """
    Cierra el visor si quedo abierto.

    destroyWindow revienta con "NULL window" si la ventana ya la cerro el
    operador con la X, y esa excepcion, suelta, se llevaba el analisis entero
    por delante.
    """
    try:
        cv2.destroyWindow(titulo)
        cv2.waitKey(1)   # que OpenCV alcance a procesar el cierre
    except cv2.error:
        pass


def cerrar_aperturas_pendientes(estados):
    """
    Cierra las aperturas que quedaron en curso al terminar la sesion.

    Sin esto el ultimo evento se queda con hora_cierre en null y esa puerta
    figura abierta para siempre en los reportes.
    """
    for estado in estados.values():
        if estado.abierta_desde:
            print(f"[VIVO] Cerrando la apertura en curso de {estado.nombre}...")
            estado.forzar_cierre(datetime.now())


def resumen(puerta_id, estados, publicador, analizados, transcurrido, lector, motivo):
    print("\n" + "=" * 62)
    print(f"SESION DE ANALISIS - {puerta_id}")
    print("=" * 62)
    print(f"  Motivo de termino   : {motivo}")
    print(f"  Duracion            : {transcurrido:.1f}s")
    print(f"  Frames analizados   : {analizados} ({analizados / max(transcurrido, 0.1):.1f} fps)")
    print(f"  Frames descartados  : {lector.frames_perdidos} (llegaron mientras YOLO procesaba)")
    print(f"  Reconexiones        : {lector.desconexiones}")
    print(f"  Eventos en la base  : {publicador.registrados}")
    print(f"  Eventos respaldados : {publicador.fallidos}")

    for estado in estados.values():
        print(f"\n  {estado.nombre}: {len(estado.eventos)} evento(s), estado final = {estado.estado}")
        for ev in estado.eventos:
            marca = "ALERTA" if ev["supero_umbral"] else "ok"
            print(f"    {ev['apertura'][11:19]} -> {ev['cierre'][11:19]}  "
                f"({ev['duracion_segundos']}s) [{marca}]")
    print("=" * 62)


if __name__ == "__main__":
    sys.exit(main())
