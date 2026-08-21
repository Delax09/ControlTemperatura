import cv2
import json
import os
from datetime import datetime
from pathlib import Path
from ultralytics import YOLO

MODEL_PATH = "runs/detect/modelo_puerta_det-3/weights/best.pt"  
JSON_LOG_PATH = "alertas_puerta.json"
TARGET_CLASS = "puerta_abierta"  # Asegúrate de que coincida con tu data.yaml
CONF_THRESHOLD = 0.50

def registrar_alerta(confianza):
    nueva_alerta = {
        "timestamp": datetime.now().isoformat(),
        "evento": "puerta_abierta",
        "confianza": round(float(confianza), 2)
    }

    # Cargar datos previos si existen
    if os.path.exists(JSON_LOG_PATH):
        try:
            with open(JSON_LOG_PATH, "r", encoding="utf-8") as f:
                datos = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            datos = []
    else:
        datos = []

    datos.append(nueva_alerta)

    # Guardar con indentación legible
    with open(JSON_LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(datos, f, indent=4, ensure_ascii=False)
    
    print(f"[ALERTA REGISTRADA] {nueva_alerta}")

# Inicializar modelo y captura
model = YOLO(MODEL_PATH)
cap = cv2.VideoCapture(0)  # 0 para webcam o ruta de video

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    results = model(frame, conf=CONF_THRESHOLD, verbose=False)

    for r in results:
        for box in r.boxes:
            cls_id = int(box.cls[0])
            label = model.names[cls_id]
            conf = float(box.conf[0])

            if label.lower() == TARGET_CLASS.lower():
                registrar_alerta(conf)

    cv2.imshow("Detección", results[0].plot())
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()

def main():
    print("Iniciando reconocimiento...")
    # Puede ser una imagen (.jpg, .jpeg, .png) o un video (.mp4, .avi, .mov)
    entrada_prueba = Path("Videos/VideoEntrenar9.mp4")
    if not entrada_prueba.is_file():
        raise FileNotFoundError(f"No se encontró el archivo de entrada: {entrada_prueba}")
    resultados = model.predict(
        source=str(entrada_prueba),
        show=True,       
        save=True,       
        conf=0.5         
    )
    print("¡Reconocimiento finalizado!")
    print("El resultado con las predicciones se guardó en la carpeta: runs/detect/predict/")

if __name__ == '__main__':
    main()


