import os

import cv2
import requests
import json
import numpy as np
from datetime import datetime, timezone
from ultralytics import YOLO

# --- 1. CONFIGURACIÓN DEL MICROSERVICIO ---
API_URL = "http://127.0.0.1:8000/api/"
RUTA_MODELO = "runs/detect/runs/detect/modelo_puerta_robusto-3/weights/best.pt"
CLASE_OBJETIVO = "puerta_abierta"
UMBRAL_CONFIANZA = 0.60
FRAMES_CONFIRMACION = 5

# Funciones de comunicación con el Backend
def obtener_puertas_y_rois():
    try:
        res = requests.get(f"{API_URL}doors/")
        res.raise_for_status()
        return res.json()
    except Exception as e:
        print(f"Error conectando al backend: {e}")
        return []

def notificar_puerta_abierta(door_id):
    payload = {
        "door": door_id,
        "event_type": "abierta",
        "open_time": datetime.now(timezone.utc).isoformat()
    }
    try:
        res = requests.post(f"{API_URL}events/", json=payload)
        res.raise_for_status()
        return res.json().get('event_id')
    except Exception as e:
        print(f"Error al registrar apertura: {e}")
        return None

def notificar_puerta_cerrada(event_id):
    if not event_id: return
    payload = {"close_time": datetime.now(timezone.utc).isoformat()}
    try:
        requests.patch(f"{API_URL}events/{event_id}/", json=payload)
    except Exception as e:
        print(f"Error al registrar cierre: {e}")


# --- 2. CLASE DE SEGUIMIENTO INDEPENDIENTE ---
class SeguimientoPuertaAPI:
    """Maneja el estado de la puerta consumiendo los datos de la API REST"""
    def __init__(self, door_data):
        self.door_id = door_data['door_id']
        self.nombre = door_data['name']
        self.puntos_roi = json.loads(door_data['roi']) # Cargamos el JSON de la BD
        
        self.estado = "cerrada"
        self.hora_apertura = None
        self.evento_id = None
        self.confianza = 0.0
        self.frames_abierta = 0
        self.frames_cerrada = 0

    def get_poligono(self, forma_frame):
        alto, ancho = forma_frame[:2]
        pts = [(int(x * ancho), int(y * alto)) for x, y in self.puntos_roi]
        return np.array(pts, dtype=np.int32)

    def fraccion_dentro(self, caja, forma_frame):
        """Calcula cuánto de la detección intersecta con la ROI de la BD"""
        poly = self.get_poligono(forma_frame)
        x1, y1, x2, y2 = map(int, caja)
        box_poly = np.array([[x1,y1], [x2,y1], [x2,y2], [x1,y2]], dtype=np.int32)
        
        mask_roi = np.zeros(forma_frame[:2], dtype=np.uint8)
        mask_box = np.zeros(forma_frame[:2], dtype=np.uint8)
        
        cv2.fillPoly(mask_roi, [poly], 255)
        cv2.fillPoly(mask_box, [box_poly], 255)
        
        interseccion = cv2.bitwise_and(mask_roi, mask_box)
        area_interseccion = cv2.countNonZero(interseccion)
        area_caja = cv2.countNonZero(mask_box)
        
        return area_interseccion / area_caja if area_caja > 0 else 0

    def actualizar(self, detectada, confianza):
        self.confianza = confianza if detectada else 0.0
        if detectada:
            self.frames_abierta += 1
            self.frames_cerrada = 0
        else:
            self.frames_cerrada += 1
            self.frames_abierta = 0

        if self.estado == "cerrada" and self.frames_abierta >= FRAMES_CONFIRMACION:
            self.estado = "abierta"
            self.hora_apertura = datetime.now()
            print(f"[{self.nombre}] APERTURA detectada. Enviando a API...")
            self.evento_id = notificar_puerta_abierta(self.door_id)

        elif self.estado == "abierta" and self.frames_cerrada >= FRAMES_CONFIRMACION:
            self.estado = "cerrada"
            if self.hora_apertura:
                duracion = (datetime.now() - self.hora_apertura).total_seconds()
                print(f"[{self.nombre}] CIERRE detectado ({duracion:.1f}s). Actualizando API...")
                notificar_puerta_cerrada(self.evento_id)
            self.hora_apertura = None
            self.evento_id = None


# --- 3. INICIALIZACIÓN DE YOLO Y VIDEO ---
modificado = datetime.fromtimestamp(os.path.getmtime(RUTA_MODELO)).strftime("%Y-%m-%d %H:%M")
print(f"[PRUEBA] Pesos:   {RUTA_MODELO}")
print(f"[PRUEBA] Corrida: {os.path.basename(os.path.dirname(os.path.dirname(RUTA_MODELO)))}  ({modificado})")
model = YOLO(RUTA_MODELO)
print(f"[PRUEBA] Clases:  {', '.join(str(n) for n in model.names.values())}")
origen_video = 0 # Cambia esto por tu RTSP si aplica
cap = cv2.VideoCapture(origen_video)

print("Descargando puertas desde la Base de Datos...")
puertas_bd = obtener_puertas_y_rois()
seguimientos = [SeguimientoPuertaAPI(p) for p in puertas_bd]

if not seguimientos:
    print("ADVERTENCIA: No se encontraron puertas en la base de datos.")

# --- 4. BUCLE PRINCIPAL (while True) ---
while cap.isOpened():
    ret, frame = cap.read()
    if not ret: break

    resultados = model(frame, conf=UMBRAL_CONFIANZA, verbose=False)
    detecciones = [(box.xyxy[0], float(box.conf[0])) for r in resultados for box in r.boxes if model.names[int(box.cls[0])] == CLASE_OBJETIVO]

    # Asignar detecciones a la puerta correspondiente
    cajas_por_zona = {seg.nombre: [] for seg in seguimientos}
    for caja, conf in detecciones:
        mejor_zona, mejor_solapamiento = None, 0.2 # Solapamiento mínimo del 20%
        for seg in seguimientos:
            solapamiento = seg.fraccion_dentro(caja, frame.shape)
            if solapamiento >= mejor_solapamiento:
                mejor_solapamiento = solapamiento
                mejor_zona = seg.nombre
        if mejor_zona:
            cajas_por_zona[mejor_zona].append(conf)

    # Actualizar estados y dibujar
    frame_display = cv2.resize(frame, (1024, 576))
    y_texto = 40
    
    for seg in seguimientos:
        confianza_max = max(cajas_por_zona[seg.nombre], default=0.0)
        seg.actualizar(bool(cajas_por_zona[seg.nombre]), confianza_max)
        
        # Dibujar polígonos
        poly = seg.get_poligono(frame_display.shape)
        color = (0, 0, 255) if seg.estado == "abierta" else (0, 255, 0)
        cv2.polylines(frame_display, [poly], True, color, 2)
        cv2.putText(frame_display, f"{seg.nombre}: {seg.estado.upper()}", (20, y_texto), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        y_texto += 32

    cv2.imshow("Monitor YOLO Independiente", frame_display)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()