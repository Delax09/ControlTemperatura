import cv2
import requests
import os
from datetime import datetime
from ultralytics import YOLO

# --- 1. CONFIGURACIÓN ---
RUTA_VIDEO = "Videos/VideoEntrenar9.mp4"
RUTA_MODELO = "yolov8n.pt"  # Cambia a tu modelo entrenado (ej. runs/detect/.../best.pt)

API_URL = "http://127.0.0.1:8000/api/eventos/"
TOKEN_API = os.getenv("DJANGO_TOKEN_API")
HEADERS = {'Authorization': f'Token {TOKEN_API}'}

# --- 2. INICIALIZACIÓN ---
model = YOLO(RUTA_MODELO)
cap = cv2.VideoCapture(RUTA_VIDEO)

CLASE_OBJETIVO = "puerta_abierta"
UMBRAL_CONFIANZA = 0.50

# Variables de estado
estado_actual = "cerrada"
hora_apertura_dt = None
evento_id_actual = None

print(f"Iniciando análisis del video: {RUTA_VIDEO}")

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    # Realizar inferencia
    resultados = model(frame, conf=UMBRAL_CONFIANZA, verbose=False)
    
    detectada_abierta = False
    confianza_frame = 0.0
    caja_detectada = None

    # Analizar detecciones
    for r in resultados:
        for box in r.boxes:
            clase = model.names[int(box.cls[0])]
            conf = float(box.conf[0])

            if clase == CLASE_OBJETIVO:
                detectada_abierta = True
                confianza_frame = max(confianza_frame, conf)
                caja_detectada = box.xyxy[0] # Guardar coordenadas para dibujar

    # --- 3. LÓGICA DE EVENTOS Y DURACIÓN ---
    
    # CASO A: La puerta se ABRE (Flanco de subida)
    if detectada_abierta and estado_actual == "cerrada":
        estado_actual = "abierta"
        hora_apertura_dt = datetime.now()
        print(f"\n[{hora_apertura_dt.strftime('%H:%M:%S')}] ¡Puerta abierta! Registrando inicio...")

        # Guardar imagen en memoria
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
                print(f" -> Evento #{evento_id_actual} creado en Django.")
        except Exception as e:
            print(f" -> Error de red al abrir: {e}")

    # CASO B: La puerta se CIERRA (Flanco de bajada)
    elif not detectada_abierta and estado_actual == "abierta":
        estado_actual = "cerrada"
        hora_cierre_dt = datetime.now()
        
        # Calcular el tiempo que pasó abierta
        if hora_apertura_dt and evento_id_actual:
            duracion = (hora_cierre_dt - hora_apertura_dt).total_seconds()
            print(f"[{hora_cierre_dt.strftime('%H:%M:%S')}] Puerta cerrada. Duración total: {duracion:.2f} segundos.")
            
            datos_cierre = {
                "hora_cierre": hora_cierre_dt.isoformat(),
                "duracion_segundos": round(duracion, 2)
            }
            
            try:
                # Usamos PATCH para actualizar el registro existente con la duración
                res = requests.patch(f"{API_URL}{evento_id_actual}/", data=datos_cierre, headers=HEADERS)
                if res.status_code == 200:
                    print(f" -> Evento #{evento_id_actual} actualizado con éxito.")
            except Exception as e:
                print(f" -> Error de red al cerrar: {e}")
            
            # Resetear variables
            hora_apertura_dt = None
            evento_id_actual = None

    # --- 4. VISUALIZACIÓN EN PANTALLA ---
    frame_display = cv2.resize(frame, (1024, 576))
    escala_x = 1024 / frame.shape[1]
    escala_y = 576 / frame.shape[0]

    # Dibujar cuadro delimitador si está abierta
    if detectada_abierta and caja_detectada is not None:
        x1, y1, x2, y2 = map(int, caja_detectada)
        cv2.rectangle(frame_display, (int(x1*escala_x), int(y1*escala_y)), (int(x2*escala_x), int(y2*escala_y)), (0, 255, 0), 2)

    # Textos de análisis
    color_estado = (0, 0, 255) if estado_actual == "abierta" else (0, 255, 0)
    cv2.putText(frame_display, f"Estado: {estado_actual.upper()}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, color_estado, 2)
    cv2.putText(frame_display, f"Confianza: {confianza_frame:.2f}", (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    # Mostrar tiempo en vivo si la puerta sigue abierta
    if estado_actual == "abierta" and hora_apertura_dt:
        tiempo_actual = (datetime.now() - hora_apertura_dt).total_seconds()
        cv2.putText(frame_display, f"Tiempo abierta: {tiempo_actual:.1f}s", (20, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)

    cv2.imshow("Monitor de Puertas - ML", frame_display)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()