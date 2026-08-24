from ultralytics import YOLO

model = YOLO("yolov8n.pt")
def main():
    print("Iniciando entrenamiento...")
    results = model.train(
        data="data.yaml",
        epochs=60,
        imgsz=640,
        batch=8,
        name="modelo_puerta_det",
        device="cpu",
        patience=20,
        plots=True
    )

    print("Entrenamiento finalizado.")

if __name__ == "__main__":
    main()