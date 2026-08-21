import os
import json
import cv2
import unicodedata
from datetime import datetime
from pathlib import Path
from ultralytics import YOLO

# --- CONFIGURACIÓN GLOBAL ---
MODEL_PATH = "runs/detect/modelo_puerta_det-3/weights/best.pt"
OUTPUT_DIR = "alertas"  # Carpeta de salida para el registro de alertas
JSON_FILE = "alertas_puerta.json"
JSON_LOG_PATH = os.path.join(OUTPUT_DIR, JSON_FILE)

TARGET_CLASS = "puerta_abierta"
CONF_THRESHOLD = 0.50 
VIDEO_PATH = Path("Videos/VideoEntrenar9.mp4")  # Usa 0 para webcam o la ruta al archivo de video 


def normalizar_texto(texto: str) -> str:
    """Normaliza texto eliminando acentos, espacios extra y guiones bajos."""
    nfkd = unicodedata.normalize('NFKD', texto)
    limpio = "".join([c for c in nfkd if not unicodedata.combining(c)])
    return limpio.lower().replace("_", " ").strip()


def registrar_alerta(confianza: float, etiqueta: str, json_path: str = JSON_LOG_PATH):
    """Guarda un registro de alerta dentro del archivo JSON en la carpeta especificada."""
    # Asegurar que el directorio de salida exista
    directorio = os.path.dirname(json_path)
    if directorio:
        os.makedirs(directorio, exist_ok=True)

    nueva_alerta = {
        "timestamp": datetime.now().isoformat(), 
        "evento": "puerta_abierta", 
        "etiqueta_detectada": etiqueta,
        "confianza": round(float(confianza), 2) 
    }

    datos = []
    if os.path.exists(json_path): 
        try:
            with open(json_path, "r", encoding="utf-8") as f: 
                contenido = json.load(f) 
                if isinstance(contenido, list):
                    datos = contenido
        except (json.JSONDecodeError, FileNotFoundError): 
            datos = [] 

    datos.append(nueva_alerta) 

    with open(json_path, "w", encoding="utf-8") as f: 
        json.dump(datos, f, indent=4, ensure_ascii=False) 

    print(f"[ALERTA REGISTRADA en {json_path}] {nueva_alerta}") 


def procesar_fuente(modelo: YOLO, fuente, target_class: str = TARGET_CLASS, conf_threshold: float = CONF_THRESHOLD):
    """Lee fotograma a fotograma la fuente (cámara o video), detecta objetos y registra alertas."""
    # Convertir Path a string o int si es número
    origen = str(fuente) if isinstance(fuente, Path) else fuente
    cap = cv2.VideoCapture(origen) 

    if not cap.isOpened():
        raise RuntimeError(f"No se pudo abrir la fuente de video/cámara: {fuente}")

    target_normalizado = normalizar_texto(target_class)
    print(f"Buscando objetivo: '{target_class}' (clases del modelo: {modelo.names})")

    while cap.isOpened(): 
        ret, frame = cap.read() 
        if not ret:
            break 

        resultados = modelo(frame, conf=conf_threshold, verbose=False) 

        for r in resultados: 
            for box in r.boxes: 
                cls_id = int(box.cls[0]) 
                label_real = modelo.names[cls_id] 
                conf = float(box.conf[0]) 

                if normalizar_texto(label_real) == target_normalizado:
                    registrar_alerta(confianza=conf, etiqueta=label_real) 

        # Mostrar visualización
        cv2.imshow("Monitoreo de Detección", resultados[0].plot()) 
        if cv2.waitKey(1) & 0xFF == ord('q'): 
            break 

    cap.release() 
    cv2.destroyAllWindows() 


def main():
    print("Iniciando reconocimiento...") 

    # Validar archivo si es una ruta local
    if isinstance(VIDEO_PATH, Path) and not VIDEO_PATH.is_file(): 
        raise FileNotFoundError(f"No se encontró el archivo de entrada: {VIDEO_PATH}") 

    # Cargar modelo
    modelo = YOLO(MODEL_PATH) 

    # Procesar fuente y disparar alertas
    procesar_fuente(
        modelo=modelo,
        fuente=VIDEO_PATH,
        target_class=TARGET_CLASS,
        conf_threshold=CONF_THRESHOLD
    )

    print(f"Proceso finalizado. Registros guardados en: {JSON_LOG_PATH}")


if __name__ == '__main__':
    main() 