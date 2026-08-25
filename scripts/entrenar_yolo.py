from ultralytics import YOLO

# 1. Usar YOLOv8 Small (yolov8s.pt) en lugar de Nano (yolov8n.pt) para mayor extracción de rasgos
model = YOLO('yolov8s.pt')

# 2. Entrenar con mayor resolución y data augmentation
model.train(
    data='dataset/data.yaml',
    epochs=100,
    imgsz=640,
    batch=16,          
    mosaic=1.0,            # Fusión de imágenes para detectar en distintas escalas
    mixup=0.1,             # Mezcla de frames para robustez ante oclusiones
    project='runs/detect',
    name='modelo_puerta_robusto'
)