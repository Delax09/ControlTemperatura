import cv2
import time
import requests
from ultralytics import YOLO

# Importar configuración y conexión de cámara
from app.camara_stream import iniciar_captura
from app.config import API_URL, HEADERS_API

# Ruta de tu mejor modelo (la que compartiste al principio)
RUTA_MODELO = r"runs/detect/runs/detect/modelo_puerta_robusto/weights/best.pt"

def main():
    print("[INFO] Cargando modelo YOLOv8...")
    modelo = YOLO(RUTA_MODELO)

    print("[INFO] Iniciando conexión de video CCTV...")
    try:
        cap = iniciar_captura()
    except ConnectionError as e:
        print(e)
        return

    while True:
        ret, frame = cap.read()
        
        # 1. Manejo de micro-cortes de red de la cámara IP
        if not ret:
            print("[CCTV] Advertencia: Se perdió la señal del frame. Intentando reconectar...")
            cap.release()
            try:
                cap = iniciar_captura()
                continue
            except ConnectionError:
                print("[CCTV] Imposible reconectar. Deteniendo análisis.")
                break

        # 2. Análisis con YOLOv8 (stream=True ahorra memoria)
        resultados = modelo(frame, stream=True, verbose=False)
        
        # 3. Procesar las detecciones
        for r in resultados:
            cajas = r.boxes
            for caja in cajas:
                # Obtener coordenadas de la caja
                x1, y1, x2, y2 = map(int, caja.xyxy[0])
                
                # Obtener la clase detectada
                clase_id = int(caja.cls[0])
                nombre_clase = modelo.names[clase_id]
                confianza = float(caja.conf[0])
                
                # Solo tomamos detecciones con buena confianza
                if confianza > 0.60:
                    # Dibujar la caja en el video para verlo en pantalla
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
                    cv2.putText(frame, f"{nombre_clase} {confianza:.2f}", (x1, y1 - 10), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

        # 4. Mostrar el monitoreo en vivo en pantalla
        cv2.imshow("Monitoreo CCTV - Andenes", frame)

        # Presiona la tecla 'q' para salir del video
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Liberar recursos al terminar
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()