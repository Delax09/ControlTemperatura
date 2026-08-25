import cv2
import requests
import sys
import os
from datetime import datetime
from ultralytics import YOLO

# Añadir el directorio raíz al PATH para poder importar la carpeta 'app'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importar variables y funciones desde nuestro módulo de configuración
from app.config import API_URL, HEADERS_API, obtener_origen_video

# --- 1. INICIALIZACIÓN ---
RUTA_MODELO = "yolov8n.pt"  # Cambiar por la ruta de tu modelo entrenado
CLASE_OBJETIVO = "puerta_abierta"
UMBRAL_CONFIANZA = 0.60

model = YOLO(RUTA_MODELO)
origen_video = obtener_origen_video()
cap = cv2.VideoCapture(origen_video)

# Variables de estado
estado_actual = "cerrada"
hora_apertura_dt = None
evento_id_actual = None

print(f"Iniciando análisis. Origen de video: {origen_video}")

# --- 2. BUCLE PRINCIPAL DE INFERENCIA ---
while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        print("Error de lectura o fin de la transmisión. Intentando reconectar...")
        break

    resultados = model(frame, conf=UMBRAL_CONFIANZA, verbose=False)
    
    detectada_abierta = False
    confianza_frame = 0.0
    caja_detectada = None

    for r in resultados:
        for box in r.boxes:
            clase = model.names[int(box.cls[0])]
            conf = float(box.conf[0])

            if clase == CLASE_OBJETIVO:
                detectada_abierta = True
                confianza_frame = max(confianza_frame, conf)
                caja_detectada = box.xyxy[0]

    # --- 3. LÓGICA DE EVENTOS HACIA LA API ---
    # CASO A: Puerta se abre
    if detectada_abierta and estado_actual == "cerrada":
        estado_actual = "abierta"
        hora_apertura_dt = datetime.now()
        
        _, buffer = cv2.imencode('.jpg', frame)
        datos = {"evento": "puerta_abierta", "hora_apertura": hora_apertura_dt.isoformat(), "confianza_promedio": round(confianza_frame, 2)}
        archivos = {"imagen": (f"alerta_{hora_apertura_dt.strftime('%Y%m%d_%H%M%S')}.jpg", buffer.tobytes(), "image/jpeg")}
        
        try:
            res = requests.post(API_URL, data=datos, files=archivos, headers=HEADERS_API)
            if res.status_code == 201:
                evento_id_actual = res.json().get('id')
        except Exception as e:
            print(f"Error conexión API: {e}")

    # CASO B: Puerta se cierra
    elif not detectada_abierta and estado_actual == "abierta":
        estado_actual = "cerrada"
        hora_cierre_dt = datetime.now()
        
        if hora_apertura_dt and evento_id_actual:
            duracion = (hora_cierre_dt - hora_apertura_dt).total_seconds()
            datos_cierre = {"hora_cierre": hora_cierre_dt.isoformat(), "duracion_segundos": round(duracion, 2)}
            try:
                requests.patch(f"{API_URL}{evento_id_actual}/", data=datos_cierre, headers=HEADERS_API)
            except Exception as e:
                pass
            hora_apertura_dt = None
            evento_id_actual = None

    # --- 4. VISUALIZACIÓN ---
    frame_display = cv2.resize(frame, (1024, 576))
    escala_x = 1024 / frame.shape[1]
    escala_y = 576 / frame.shape[0]

    if detectada_abierta and caja_detectada is not None:
        x1, y1, x2, y2 = map(int, caja_detectada)
        cv2.rectangle(frame_display, (int(x1*escala_x), int(y1*escala_y)), (int(x2*escala_x), int(y2*escala_y)), (0, 255, 0), 2)

    color_estado = (0, 0, 255) if estado_actual == "abierta" else (0, 255, 0)
    cv2.putText(frame_display, f"Estado: {estado_actual.upper()}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, color_estado, 2)
    cv2.putText(frame_display, f"Confianza: {confianza_frame:.2f}", (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    if estado_actual == "abierta" and hora_apertura_dt:
        tiempo_actual = (datetime.now() - hora_apertura_dt).total_seconds()
        cv2.putText(frame_display, f"Tiempo: {tiempo_actual:.1f}s", (20, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)

    cv2.imshow("Monitor YOLO", frame_display)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()