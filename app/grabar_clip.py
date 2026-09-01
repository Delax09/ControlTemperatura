"""
Graba un clip de la cámara en vivo para generar material de reentrenamiento.

El clip queda en Videos/ con el mismo formato que los VideoEntrenar*.mp4, listo
para pasarlo por vision_worker/scripts/extraer_frames.py.

Uso:
    python -m app.grabar_clip                        # 30s del sub-stream
    python -m app.grabar_clip --segundos 60
    python -m app.grabar_clip --stream principal     # 1080p, para etiquetar mejor
    python -m app.grabar_clip --nombre puerta_abriendo
    python -m app.grabar_clip --extraer              # graba y extrae los frames
    python -m app.grabar_clip --extraer --min-dif 0  # extraer sin filtrar repetidos

Controles: Ctrl+C corta la grabación y guarda lo capturado hasta ese momento.
"""
import argparse
import os
import sys
import time
from datetime import datetime

import cv2

from app.config import construir_url_rtsp, obtener_origen_video, ocultar_password, USAR_CAMARA_IP

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR_VIDEOS = os.path.join(BASE_DIR, "Videos")

RUTAS_STREAM = {
    "principal": "/cam/realmonitor?channel=1&subtype=0",   # 1920x1080
    "sub": "/cam/realmonitor?channel=1&subtype=1",         # 352x240
}

SEGUNDOS_MEDICION = 2.0   # cuánto observar el stream para medir su ritmo real


def medir_fps(cap, segundos=SEGUNDOS_MEDICION):
    """
    Mide el ritmo real de entrega del stream.

    CAP_PROP_FPS es lo que la cámara *declara*, no lo que entrega: el sub-stream
    de esta Dahua declara 30 fps. Si se graba con el valor declarado, el mp4
    queda a velocidad equivocada y los frames extraídos no corresponden al
    tiempo real, que es justo lo que se necesita para medir tiempos de puerta.
    """
    declarado = cap.get(cv2.CAP_PROP_FPS) or 0
    leidos = 0
    inicio = time.time()

    while time.time() - inicio < segundos:
        ok, _ = cap.read()
        if not ok:
            break
        leidos += 1

    transcurrido = time.time() - inicio
    medido = leidos / transcurrido if transcurrido > 0 else 0

    print(f"[REC] FPS declarado por la camara: {declarado:.0f}")
    print(f"[REC] FPS real medido            : {medido:.1f}")

    if medido < 1:
        print(f"[REC] Medicion no confiable, usando el declarado.")
        return declarado or 15.0
    return medido


def grabar(url, ruta_salida, segundos, fps_forzado=None):
    """Graba el stream a mp4. Retorna (ruta, frames, duracion_real, fps)."""
    cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
    if not cap.isOpened():
        print(f"[ERROR] No se pudo abrir el stream.")
        return None

    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    ancho = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    alto = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"[REC] Resolucion: {ancho}x{alto}")

    fps = fps_forzado or medir_fps(cap)

    os.makedirs(os.path.dirname(ruta_salida), exist_ok=True)
    escritor = cv2.VideoWriter(ruta_salida, cv2.VideoWriter_fourcc(*"mp4v"), fps, (ancho, alto))
    if not escritor.isOpened():
        print("[ERROR] No se pudo crear el archivo de video.")
        cap.release()
        return None

    print(f"\n[REC] Grabando {segundos:.0f}s... (Ctrl+C para cortar antes)\n")
    frames = 0
    inicio = time.time()
    ultimo_aviso = 0

    try:
        while True:
            transcurrido = time.time() - inicio
            if transcurrido >= segundos:
                break

            ok, frame = cap.read()
            if not ok:
                print("[REC] Se corto el stream.")
                break

            escritor.write(frame)
            frames += 1

            # Barra de progreso en una sola linea
            if transcurrido - ultimo_aviso >= 1.0:
                ultimo_aviso = transcurrido
                avance = int(30 * transcurrido / segundos)
                barra = "#" * avance + "-" * (30 - avance)
                sys.stdout.write(f"\r  [{barra}] {transcurrido:4.1f}s / {segundos:.0f}s  {frames} frames")
                sys.stdout.flush()

    except KeyboardInterrupt:
        print("\n[REC] Cortado por el usuario.")
    finally:
        duracion = time.time() - inicio
        cap.release()
        escritor.release()

    print()
    return ruta_salida, frames, duracion, fps


def extraer_frames(ruta_video, cada_n=15, diferencia_minima=0.0):
    """
    Extrae frames del clip al mismo formato que espera el flujo de etiquetado.

    Con diferencia_minima > 0 se descartan los frames casi idénticos al último
    guardado. Importa: 30s de una puerta que no se mueve dan decenas de copias
    de la misma imagen, y etiquetarlas no aporta información al modelo, solo
    refuerza el sesgo hacia la escena que ya clasifica mal.
    """
    nombre = os.path.splitext(os.path.basename(ruta_video))[0]
    carpeta = os.path.join(BASE_DIR, f"dataset_{nombre}")
    os.makedirs(carpeta, exist_ok=True)

    cap = cv2.VideoCapture(ruta_video)
    total, guardados, descartados = 0, 0, 0
    referencia = None

    while cap.isOpened():
        ok, frame = cap.read()
        if not ok:
            break

        if total % cada_n == 0:
            if diferencia_minima > 0:
                gris = cv2.cvtColor(cv2.resize(frame, (160, 120)), cv2.COLOR_BGR2GRAY)
                if referencia is not None:
                    if float(cv2.absdiff(gris, referencia).mean()) < diferencia_minima:
                        descartados += 1
                        total += 1
                        continue
                referencia = gris

            cv2.imwrite(os.path.join(carpeta, f"puerta_{guardados:04d}.jpg"), frame)
            guardados += 1
        total += 1
    cap.release()

    print(f"[REC] {guardados} frames extraidos en dataset_{nombre}/")
    if descartados:
        print(f"[REC] {descartados} descartados por ser casi identicos al anterior")
    if guardados <= 2 and diferencia_minima > 0:
        print("[AVISO] Casi no hubo variacion en el clip. Para reentrenar necesitas")
        print("        material donde la puerta se abra y se cierre de verdad.")
    return carpeta, guardados


def main():
    parser = argparse.ArgumentParser(description="Graba un clip de la camara para reentrenamiento")
    parser.add_argument("--segundos", type=float, default=30, help="Duracion del clip (def. 30)")
    parser.add_argument("--stream", choices=["principal", "sub"], default="sub",
                        help="principal = 1080p (mejor para etiquetar), sub = 352x240 (lo que ve el modelo en produccion)")
    parser.add_argument("--nombre", help="Nombre del archivo, sin extension (def. fecha y hora)")
    parser.add_argument("--extraer", action="store_true", help="Extraer los frames al terminar")
    parser.add_argument("--cada", type=int, default=15, help="Con --extraer, guardar 1 de cada N frames (def. 15)")
    parser.add_argument("--min-dif", type=float, default=2.0,
                        help="Con --extraer, descartar frames cuya diferencia con el anterior sea menor a esto (0 = guardar todos, def. 2.0)")
    parser.add_argument("--fps", type=float, help="Forzar los fps del archivo en vez de medirlos")
    args = parser.parse_args()

    if not USAR_CAMARA_IP:
        print("[AVISO] USAR_CAMARA_IP=False en el .env: se grabara del video local, no de la camara.")
        url = obtener_origen_video()
    else:
        url = construir_url_rtsp(ruta=RUTAS_STREAM[args.stream])

    nombre = args.nombre or f"camara_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    ruta = os.path.join(DIR_VIDEOS, f"{nombre}.mp4")

    print(f"[REC] Origen : {ocultar_password(url)}")
    print(f"[REC] Destino: Videos/{nombre}.mp4")

    resultado = grabar(url, ruta, args.segundos, args.fps)
    if not resultado:
        return 1

    ruta, frames, duracion, fps = resultado
    tamano = os.path.getsize(ruta) / 1_048_576

    print("\n" + "=" * 58)
    print(f"  Archivo   : Videos/{os.path.basename(ruta)}")
    print(f"  Duracion  : {duracion:.1f}s")
    print(f"  Frames    : {frames} ({frames / max(duracion, 0.1):.1f} fps reales)")
    print(f"  Grabado a : {fps:.1f} fps")
    print(f"  Tamano    : {tamano:.1f} MB")
    print("=" * 58)

    if args.extraer:
        print()
        extraer_frames(ruta, args.cada, args.min_dif)

    return 0


if __name__ == "__main__":
    sys.exit(main())
