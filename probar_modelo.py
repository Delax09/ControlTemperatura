from ultralytics import YOLO
from pathlib import Path

# 1. Cargar tu modelo entrenado
# YOLO guarda el mejor resultado por defecto en esta ruta:
ruta_modelo = "runs/detect/modelo_puerta_det/weights/best.pt" 
model = YOLO(ruta_modelo)

def main():
    print("Iniciando reconocimiento...")
    
    # Puede ser una imagen (.jpg, .jpeg, .png) o un video (.mp4, .avi, .mov)
    entrada_prueba = Path("Puerta.png")
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