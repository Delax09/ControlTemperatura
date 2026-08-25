import cv2
import os
import requests
from datetime import datetime
from ultralytics import YOLO

RUTA_VIDEO = "Videos/VideoEntrenar9.mp4"
RUTA_MODELO = "runs/detect/modelo_puerta_det/weights/best.pt"
API_URL = "http://127.0.0.1:8000/api/eventos/"
TOKEN_API = TOKEN_API = os.getenv('DJANGO_TOKEN_API')
HEADERS = {'Authorization': f'Token {TOKEN_API}'}

model = YOLO(RUTA_MODELO)
cap = cv2.VideoCapture(RUTA_VIDEO)

# --- CONFIGURACIÓN DE FILTROS ---
UMBRAL_CONFIANZA = 0.55       # Ignorar detecciones dudosas < 55%
FRAMES_CONFIRMACION = 5       # Cantidad de frames seguidos para validar cambio
CLASE_OBJETIVO = "puerta_abierta"

contador_abierta = 0
contador_cerrada = 0
estado_confirmado = "cerrada"

# Variables de seguimiento de evento
evento_id_actual = None
hora_apertura_dt = None

print("Iniciando análisis robusto de video...")

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    # Inferencia con umbral mínimo
    resultados = model(frame, conf=UMBRAL_CONFIANZA, verbose=False)
    
    detectada_abierta = False
    confianza_frame = 0.0

    for r in resultados:
        for box in r.boxes:
            clase = model.names[int(box.cls[0])]
            conf = float(box.conf[0])
            if clase == CLASE_OBJETIVO:
                detectada_abierta = True
                confianza_frame = max(confianza_frame, conf)

    # 1. Filtro temporal (Anti-rebote)
    if detectada_abierta:
        contador_abierta += 1
        contador_cerrada = 0
    else:
        contador_cerrada += 1
        contador_abierta = 0

    # 2. Transición: Puerta pasa a ABIERTA
    if contador_abierta >= FRAMES_CONFIRMACION and estado_confirmado == "cerrada":
        estado_confirmado = "abierta"
        hora_apertura_dt = datetime.now()
        
        _, buffer = cv2.imencode('.jpg', frame)
        datos = {
            "evento": "puerta_abierta",
            "hora_apertura": hora_apertura_dt.isoformat(),
            "confianza_promedio": round(confianza_frame, 2)
        }
        archivos = {"imagen": (f"alerta_{hora_apertura_dt.strftime('%Y%m%d_%H%M%S')}.jpg", buffer.tobytes(), "image/jpeg")}
        
        try:
            res = requests.post(API_URL, data=datos, files=archivos, headers=HEADERS)
            if res.status_code == 201:
                evento_id_actual = res.json().get('id')
                print(f"[ALERTA INICIADA] Evento ID #{evento_id_actual} registrado.")
        except Exception as e:
            print(f"Error de red al abrir: {e}")

    # 3. Transición: Puerta pasa a CERRADA (Completar duración)
    elif contador_cerrada >= FRAMES_CONFIRMACION and estado_confirmado == "abierta":
        estado_confirmado = "cerrada"
        hora_cierre_dt = datetime.now()
        duracion = (hora_cierre_dt - hora_apertura_dt).total_seconds()
        
        if evento_id_actual:
            datos_cierre = {
                "hora_cierre": hora_cierre_dt.isoformat(),
                "duracion_segundos": round(duracion, 2)
            }
            try:
                # Actualizar el registro existente mediante PATCH
                requests.patch(f"{API_URL}{evento_id_actual}/", data=datos_cierre, headers=HEADERS)
                print(f"[ALERTA FINALIZADA] Evento #{evento_id_actual} cerrado. Duración: {duracion:.2f}s")
            except Exception as e:
                print(f"Error de red al cerrar: {e}")
            evento_id_actual = None

    # Visualización
    cv2.putText(frame, f"Estado: {estado_confirmado.upper()}", (20, 40), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255) if estado_confirmado == "abierta" else (0, 255, 0), 2)
    cv2.imshow("Monitor", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()