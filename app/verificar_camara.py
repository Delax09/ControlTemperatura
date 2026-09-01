"""
Verificador de conexion con la camara IP.

Uso:
    python -m app.verificar_camara            -> prueba la config del .env
    python -m app.verificar_camara --buscar   -> prueba puertos y rutas comunes
"""
import os
import socket
import sys
import time

import cv2

from app.config import RUTAS_COMUNES, construir_url_rtsp, ocultar_password, obtener_origen_video

# Silenciar el ruido de FFMPEG cuando una URL no responde
os.environ.setdefault("OPENCV_FFMPEG_CAPTURE_OPTIONS", "rtsp_transport;tcp")
try:
    cv2.utils.logging.setLogLevel(cv2.utils.logging.LOG_LEVEL_SILENT)
except Exception:
    pass


def hay_red(ip, puerto, timeout=3):
    """Primer filtro: verifica que el puerto TCP este abierto antes de gastar tiempo en RTSP."""
    try:
        with socket.create_connection((ip, int(puerto)), timeout=timeout):
            return True
    except OSError:
        return False


def probar_url(url, timeout_ms=8000):
    """
    Intenta abrir la URL y leer un frame real.
    Retorna (conectado: bool, mensaje: str, frame).
    isOpened() no basta: hay camaras que abren pero nunca entregan imagen.
    """
    cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
    cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, timeout_ms)
    cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, timeout_ms)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 2)

    try:
        if not cap.isOpened():
            return False, "No se pudo abrir el stream (URL, credenciales o puerto incorrectos).", None

        ok, frame = cap.read()
        if not ok or frame is None:
            return False, "El stream abrio pero no entrego frames (revisa el canal/subtype).", None

        alto, ancho = frame.shape[:2]
        fps = cap.get(cv2.CAP_PROP_FPS) or 0
        return True, f"Conexion OK - resolucion {ancho}x{alto} @ {fps:.0f} fps", frame
    finally:
        cap.release()


def verificar_conexion(verbose=True):
    """
    Verifica la fuente configurada en el .env.
    Retorna True si hay imagen, False si no.
    """
    url = obtener_origen_video()
    if verbose:
        print(f"[CCTV] Probando: {ocultar_password(url)}")

    ip = os.getenv("CAM_IP", "").strip()
    puerto = os.getenv("CAM_PUERTO_RTSP", "554").strip()

    if url.startswith("rtsp://") and not hay_red(ip, puerto):
        if verbose:
            alertar(False, f"El puerto {puerto} de {ip} no responde. Camara apagada, IP errada o firewall.")
        return False

    conectado, mensaje, _ = probar_url(url)
    if verbose:
        alertar(conectado, mensaje)
    return conectado


def alertar(conectado, mensaje):
    """Alerta visible en consola segun el resultado."""
    if conectado:
        print(f"\n\033[92m[OK] CAMARA CONECTADA\033[0m -> {mensaje}\n")
    else:
        print(f"\n\033[91m[ALERTA] CAMARA SIN CONEXION\033[0m -> {mensaje}\n")
        try:
            # Beep audible en Windows para alertar al operador
            import winsound
            winsound.MessageBeep(winsound.MB_ICONHAND)
        except Exception:
            pass


def buscar_configuracion():
    """
    Modo descubrimiento: prueba puertos y rutas comunes hasta encontrar
    una combinacion que entregue imagen. Imprime lo que hay que poner en el .env.
    """
    ip = os.getenv("CAM_IP", "").strip()
    if not ip:
        alertar(False, "CAM_IP no esta definida en el .env")
        return None

    puertos = [p for p in ["554", os.getenv("CAM_PUERTO", "").strip(), "8554"] if p]
    puertos = list(dict.fromkeys(puertos))

    print(f"[CCTV] Buscando configuracion valida en {ip}...\n")

    abiertos = []
    for puerto in puertos:
        if hay_red(ip, puerto):
            print(f"  puerto {puerto}: ABIERTO")
            abiertos.append(puerto)
        else:
            print(f"  puerto {puerto}: cerrado / sin respuesta")

    if not abiertos:
        alertar(False, f"Ningun puerto RTSP responde en {ip}. Verifica red, VLAN o que la camara este encendida.")
        return None

    print()
    for puerto in abiertos:
        for ruta in RUTAS_COMUNES:
            url = construir_url_rtsp(ruta=ruta, puerto=puerto)
            print(f"  probando {puerto}{ruta or ' (sin ruta)'} ... ", end="", flush=True)
            conectado, mensaje, _ = probar_url(url, timeout_ms=5000)
            print("OK" if conectado else "no")

            if conectado:
                alertar(True, mensaje)
                print("Agrega esto a tu .env:\n")
                print(f"  CAM_PUERTO_RTSP = '{puerto}'")
                print(f"  CAM_ROUTE = '{ruta}'")
                print(f"  USAR_CAMARA_IP = True\n")
                return url
            time.sleep(0.3)

    alertar(False, "El puerto responde pero ninguna ruta RTSP conocida entrego imagen. "
                    "Revisa usuario/clave o consulta la ruta exacta en la web de la camara.")
    return None


if __name__ == "__main__":
    if "--buscar" in sys.argv:
        sys.exit(0 if buscar_configuracion() else 1)
    sys.exit(0 if verificar_conexion() else 1)
