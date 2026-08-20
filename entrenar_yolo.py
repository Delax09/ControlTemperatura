from ultralytics import YOLO

model = YOLO("yolov8n-seg.pt")
def main():
    print("Iniciando entrenamiento...")
    results = model.train(
        data="data.yaml",
        epochs=100,
        imgsz=640,
        batch=8,
        name="modelo_puerta_seg",
        device="cpu",
        patience=20,
        plots=True
    )

    print("Entrenamiento finalizado.")

if __name__ == "__main__":
    main()