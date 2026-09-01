import os
from urllib.parse import quote
from dotenv import load_dotenv

# Cargar las variables del archivo .env
load_dotenv()

# --- 1. CONFIGURACIÓN DE LA API ---
API_URL = "http://127.0.0.1:8000/api/eventos/"
TOKEN_API = os.getenv("DJANGO_TOKEN_API", "")
HEADERS_API = {'Authorization': f'Token {TOKEN_API}'}

# --- 2. CONFIGURACIÓN DE LA CÁMARA ---
# Interruptor para alternar entre entorno de pruebas y producción.
# Se controla desde el .env con USAR_CAMARA_IP=True
USAR_CAMARA_IP = os.getenv("USAR_CAMARA_IP", "False").strip().lower() in ("true", "1", "si", "yes")

VIDEO_LOCAL = "Videos/AndenPSP1.mp4"

# Rutas RTSP conocidas segun fabricante, para el modo de descubrimiento
RUTAS_COMUNES = [
    "/cam/realmonitor?channel=1&subtype=0",   # Dahua sub-stream 0 (principal)
    "/cam/realmonitor?channel=1&subtype=1",   # Dahua sub-stream 1 (mas liviano)
    "/Streaming/Channels/101",                # Hikvision principal
    "/Streaming/Channels/102",                # Hikvision secundario
    "/live",
    "/h264Preview_01_main",                   # Reolink
    "",                                       # Sin ruta (algunas camaras genericas)
]


def construir_url_rtsp(ruta=None, puerto=None):
    """
    Construye la URL RTSP escapando usuario y password, ya que suelen
    contener caracteres (@ : . /) que rompen la URL si van en crudo.
    """
    usuario = quote(os.getenv("CAM_USUARIO", "").strip(), safe="")
    password = quote(os.getenv("CAM_PASSWORD", "").strip(), safe="")
    ip = os.getenv("CAM_IP", "").strip()
    puerto = puerto or os.getenv("CAM_PUERTO_RTSP", "554").strip()
    ruta = RUTAS_COMUNES[0] if ruta is None else ruta

    return f"rtsp://{usuario}:{password}@{ip}:{puerto}{ruta}"


def obtener_origen_video():
    """
    Retorna la URL RTSP de la cámara si USAR_CAMARA_IP es True,
    de lo contrario retorna la ruta del video local de pruebas.
    """
    if not USAR_CAMARA_IP:
        return VIDEO_LOCAL

    ruta = os.getenv("CAM_ROUTE", "").strip()
    return construir_url_rtsp(ruta if ruta else None)


def ocultar_password(url):
    """Enmascara la clave para poder imprimir la URL en logs sin filtrarla."""
    password = quote(os.getenv("CAM_PASSWORD", "").strip(), safe="")
    return url.replace(password, "*****") if password else url
