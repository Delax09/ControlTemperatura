import cv2
import time
from app.config import obtener_origen_video, USAR_CAMARA_IP

def iniciar_captura(max_reintentos=5):
    """
    Inicia la captura de video manejando reintentos y ajustando el 
    buffer para evitar latencia en cámaras IP.
    """
    url = obtener_origen_video()
    intentos = 0
    
    while intentos < max_reintentos:
        print(f"[CCTV] Intentando conectar a: {'Cámara IP en vivo' if USAR_CAMARA_IP else 'Video local'}...")
        
        cap = cv2.VideoCapture(url)
        
        # Configuración crucial para CCTV IP: reducir buffer para evitar retraso de frames
        if USAR_CAMARA_IP:
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 2)
        
        if cap.isOpened():
            print("[CCTV] Conexión establecida con éxito.")
            return cap
        
        intentos += 1
        print(f"[CCTV] Falló la conexión. Reintentando ({intentos}/{max_reintentos}) en 5 segundos...")
        time.sleep(5)
        
    raise ConnectionError("[CCTV] Error fatal: No se pudo establecer conexión con la cámara o el video.")