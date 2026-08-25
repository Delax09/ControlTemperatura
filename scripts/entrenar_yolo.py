from ultralytics import YOLO

# Cargar modelo preentrenado (YOLOv8s ofrece mejor extracción de rasgos que el nano)
model = YOLO('yolov8s.pt')

# Entrenamiento con aumentación multi-ángulo, control de luz y early stopping
model.train(
    # --- Configuración Base ---
    data='dataset/data.yaml',
    epochs=120,
    patience=20,             # Early stopping si mAP no mejora en 20 épocas
    imgsz=640,
    batch=16,
    device='cpu',                # 0 para GPU, o 'cpu' si no cuentas con GPU dedicada
    workers=4,

    # --- Aumentación Multi-Ángulo y Perspectiva ---
    degrees=10.0,            # Rotación leve (±10°) para corregir inclinaciones de montaje
    perspective=0.001,       # Deformación de perspectiva 3D (cámaras en picado o laterales)
    shear=2.0,               # Deformación angular (cámaras instaladas en esquinas)
    scale=0.5,               # Variación de escala (distancias variables entre cámara y puerta)
    translate=0.1,           # Desplazamiento horizontal y vertical leve

    # --- Robustez de Escena e Iluminación ---
    mosaic=1.0,              # Fusión de 4 imágenes (detección en diferentes escalas)
    mixup=0.1,               # Superposición de frames (robustez ante oclusiones por personal)
    hsv_h=0.015,             # Ajuste de tono
    hsv_s=0.7,               # Ajuste de saturación de color
    hsv_v=0.4,               # Ajuste de brillo (variaciones de luz artificial, sombras y reflejos)

    # --- Salida y Registro ---
    project='runs/detect',
    name='modelo_puerta_robusto',
    save=True,
    plots=True               # Genera curvas F1, PR y matrices de confusión en runs/detect/
)