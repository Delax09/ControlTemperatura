from ultralytics import YOLO

# Cargar un modelo pre-entrenado (YOLOv8 nano es rápido y ligero, ideal para empezar)
model = YOLO("yolov8n.pt") 

def main():
    print("Iniciando el entrenamiento...")
    
    # Configuración del entrenamiento
    results = model.train(
        data="ruta/a/tu/dataset/data.yaml", # <-- CAMBIA ESTO por la ruta real a tu data.yaml
        epochs=50,                           # Número de veces que el modelo verá todo el dataset
        imgsz=640,                           # Tamaño de las imágenes (estándar de YOLO)
        batch=16,                            # Cantidad de imágenes procesadas a la vez
        name="modelo_puerta",                # Nombre de la carpeta donde se guardarán los resultados
        device="0"                           # Usa "0" si tienes GPU (Nvidia), o cambia a "cpu" si no tienes
    )
    
    print("¡Entrenamiento finalizado con éxito!")

# En Windows es buena práctica usar este bloque para evitar errores de multiprocesamiento
if __name__ == '__main__':
    main()