import cv2
import os
import requests
from datetime import datetime
from ultralytics import YOLO

# --- 1. CONFIGURACIÓN DE RUTAS ---
RUTA_VIDEO = "Videos/VideoEntrenar10.mp4"
# NOTA: Cambia 'yolov8n.pt' por la ruta de tus pesos entrenados si ya los generaste 
# (ej. 'runs/detect/train/weights/best.pt')
RUTA_MODELO = "runs/detect/modelo_puerta_det/weights/best.pt" 

# --- 2. CONFIGURACIÓN DE LA API ---
API_URL = "http://127.0.0.1:8000/api/eventos/"
# Reemplaza esto con el Token que generaste en http://127.0.0.1:8000/admin/
TOKEN_API = os.getenv('DJANGO_TOKEN_API')

# --- 3. INICIALIZACIÓN ---
model = YOLO(RUTA_MODELO)
cap = cv2.VideoCapture(RUTA_VIDEO)

# Ajusta estos nombres según las etiquetas exactas con las que entrenaste tu modelo
CLASE_PUERTA_ABIERTA = "puerta_abierta" 
CLASE_PUERTA_CERRADA = "puerta_cerrada"

estado_anterior = CLASE_PUERTA_CERRADA

print(f"Iniciando análisis del video: {RUTA_VIDEO}")

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        print("Fin del video o no se pudo leer el frame.")
        break

    # Realizar la predicción
    resultados = model(frame, verbose=False)
    
    estado_actual = CLASE_PUERTA_CERRADA
    confianza_maxima = 0.0

    # Analizar las cajas delimitadoras detectadas
    for r in resultados:
        for box in r.boxes:
            clase_id = int(box.cls[0])
            nombre_clase = model.names[clase_id]
            confianza = float(box.conf[0])

            # Si detecta la puerta abierta en el frame actual, actualiza las variables
            if nombre_clase == CLASE_PUERTA_ABIERTA:
                estado_actual = CLASE_PUERTA_ABIERTA
                confianza_maxima = max(confianza_maxima, confianza)

    # --- 4. LÓGICA DE ALERTA AL BACKEND ---
    # Detecta el cambio exacto de cerrada a abierta (Flanco de subida)
    if estado_actual == CLASE_PUERTA_ABIERTA and estado_anterior == CLASE_PUERTA_CERRADA:
        hora_actual = datetime.now()
        print(f"[{hora_actual.strftime('%H:%M:%S')}] Alerta: ¡Puerta Abierta! Enviando captura al servidor...")

        # Codificar el frame para enviarlo por HTTP
        exito, buffer = cv2.imencode('.jpg', frame)
        if exito:
            headers = {'Authorization': f'Token {TOKEN_API}'}
            datos = {
                "evento": "puerta_abierta",
                "hora_apertura": hora_actual.isoformat(),
                "confianza_promedio": round(confianza_maxima, 2)
            }
            archivos = {
                "imagen": (f"captura_{hora_actual.strftime('%Y%m%d_%H%M%S')}.jpg", buffer.tobytes(), "image/jpeg")
            }

            try:
                res = requests.post(API_URL, data=datos, files=archivos, headers=headers)
                if res.status_code == 201:
                    print(" -> [OK] Registro guardado correctamente en Django.")
                else:
                    print(f" -> [ERROR API] ({res.status_code}): {res.text}")
            except Exception as e:
                print(f" -> [ERROR DE RED] No se pudo conectar con el backend: {e}")

    # Actualizar estado para el siguiente frame
    estado_anterior = estado_actual

    # --- 5. VISUALIZACIÓN ---
    # Dibuja las cajas en el frame para poder ver el resultado en pantalla
    frame_anotado = resultados[0].plot()
    cv2.imshow("Monitor de Puertas - YOLOv8", frame_anotado)
    
    # Presiona 'q' en el teclado para detener el video antes de que termine
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()