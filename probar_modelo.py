from ultralytics import YOLO

# 1. Cargar tu modelo entrenado
# YOLO guarda el mejor resultado por defecto en esta ruta:
ruta_modelo = "runs/detect/modelo_puerta_det/weights/best.pt" 
model = YOLO(ruta_modelo)

def main():
    print("Iniciando reconocimiento en el video...")
    
    # 2. Archivo de video a analizar
    video_prueba = "VideoPrueba.mp4"  # Cambia esto por la ruta a tu video de prueba
    
    # 3. Ejecutar la predicción
    # show=True: Muestra una ventana con el video y las detecciones en tiempo real.
    # save=True: Guarda el video resultante con las cajas dibujadas.
    # conf=0.5: Solo muestra detecciones de las que esté al menos 50% seguro.
    resultados = model.predict(
        source=video_prueba,
        show=True,       
        save=True,       
        conf=0.5         
    )
    
    print("¡Reconocimiento finalizado!")
    print("El video con las predicciones se guardó automáticamente en la carpeta: runs/detect/predict/")

if __name__ == '__main__':
    main()