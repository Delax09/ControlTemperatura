import os
from dotenv import load_dotenv

# Cargar las variables del archivo .env
load_dotenv()

# --- 1. CONFIGURACIÓN DE LA API ---
API_URL = "http://127.0.0.1:8000/api/eventos/"
TOKEN_API = os.getenv("DJANGO_TOKEN_API", "")
HEADERS_API = {'Authorization': f'Token {TOKEN_API}'}

# --- 2. CONFIGURACIÓN DE LA CÁMARA ---
# Interruptor para alternar entre entorno de pruebas y producción
USAR_CAMARA_IP = False

def obtener_origen_video():
    """
    Retorna la URL RTSP de la cámara si USAR_CAMARA_IP es True, 
    de lo contrario retorna la ruta del video local de pruebas.
    """
    if not USAR_CAMARA_IP:
        return "Videos/AndenPSP1.mp4"
    
    usuario = os.getenv("CAM_USUARIO", "")
    password = os.getenv("CAM_PASSWORD", "")
    ip = os.getenv("CAM_IP", "")
    puerto = os.getenv("CAM_PUERTO", "")
    ruta = os.getenv("CAM_ROUTE", "")
    
    # Construcción estándar del protocolo RTSP
    return f"rtsp://{usuario}:{password}@{ip}:{puerto}{ruta}"