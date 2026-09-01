import cv2
import time
from app.config import obtener_origen_video, ocultar_password, USAR_CAMARA_IP
from app.verificar_camara import probar_url, alertar


def iniciar_captura(max_reintentos=5):
    """
    Inicia la captura de video manejando reintentos y ajustando el
    buffer para evitar latencia en cámaras IP.
    Alerta en cada intento fallido y al establecer la conexión.
    """
    url = obtener_origen_video()
    origen = "Cámara IP en vivo" if USAR_CAMARA_IP else "Video local"
    intentos = 0

    while intentos < max_reintentos:
        print(f"[CCTV] Intentando conectar a: {origen} ({ocultar_password(url)})...")

        conectado, mensaje, _ = probar_url(url)

        if conectado:
            cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
            if USAR_CAMARA_IP:
                # Buffer chico para evitar el retraso de frames acumulados
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 2)
            if cap.isOpened():
                alertar(True, mensaje)
                return cap
            cap.release()
            mensaje = "El stream respondió pero no se pudo reabrir la captura."

        intentos += 1
        alertar(False, f"{mensaje} Reintentando ({intentos}/{max_reintentos}) en 5 segundos...")
        time.sleep(5)

    raise ConnectionError(
        "[CCTV] Error fatal: No se pudo establecer conexión con la cámara o el video."
    )
