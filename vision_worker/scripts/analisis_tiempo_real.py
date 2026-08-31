import requests
from datetime import datetime, timezone

# URL de tu backend (Servidor 1). Si está en otra máquina, cambia el localhost por la IP.
API_URL = "http://localhost:8000/api/registrar-evento"

def enviar_alerta_backend(datos):
    try:
        respuesta = requests.post(API_URL, json=datos)
        if respuesta.status_code == 200:
            print("Datos enviados correctamente")
    except requests.exceptions.ConnectionError:
        print("Error: No se pudo conectar al Backend Django")

def obtener_puertas_y_rois():
    """Descarga las puertas y sus ROIs desde la base de datos."""
    try:
        respuesta = requests.get(f"{API_URL}doors/")
        respuesta.raise_for_status()
        return respuesta.json()
    except Exception as e:
        print(f"Error conectando al backend: {e}")
        return []

def notificar_puerta_abierta(door_id):
    """Hace un POST al backend cuando YOLO detecta la puerta abierta."""
    payload = {
        "door": door_id,
        "event_type": "abierta",
        "open_time": datetime.now(timezone.utc).isoformat()
    }
    try:
        respuesta = requests.post(f"{API_URL}events/", json=payload)
        respuesta.raise_for_status()
        # Retornamos el ID del evento creado para poder cerrarlo después
        return respuesta.json().get('event_id')
    except Exception as e:
        print(f"Error al registrar apertura: {e}")
        return None

def notificar_puerta_cerrada(event_id):
    """Hace un PATCH al backend para registrar la hora de cierre."""
    if not event_id:
        return
        
    payload = {
        "close_time": datetime.now(timezone.utc).isoformat()
    }
    try:
        requests.patch(f"{API_URL}events/{event_id}/", json=payload)
        print(f"Evento {event_id} cerrado correctamente.")
    except Exception as e:
        print(f"Error al registrar cierre: {e}")