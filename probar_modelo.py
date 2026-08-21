import os
import json
import time
import unicodedata
from datetime import datetime
from pathlib import Path
import cv2
from ultralytics import YOLO

# --- CONFIGURACIÓN GLOBAL ---
MODEL_PATH = "runs/detect/modelo_puerta_det-3/weights/best.pt"
OUTPUT_DIR = "alertas"
JSON_FILE = "registro_tiempos_puerta.json"
JSON_LOG_PATH = os.path.join(OUTPUT_DIR, JSON_FILE)

TARGET_CLASS = "puerta_abierta"
CONF_THRESHOLD = 0.50
VIDEO_PATH = Path("Videos/VideoEntrenar9.mp4")  # Usa 0 para webcam o ruta a video
TOLERANCIA_DESAPARICION_SEG = 1.0  # Segundos de gracia antes de considerar la puerta cerrada


def normalizar_texto(texto: str) -> str:
    """Normaliza texto eliminando acentos, espacios extra y guiones bajos."""
    nfkd = unicodedata.normalize('NFKD', texto)
    limpio = "".join([c for c in nfkd if not unicodedata.combining(c)])
    return limpio.lower().replace("_", " ").strip()


def registrar_duracion(inicio_iso: str, fin_iso: str, duracion: float, confianzas: list, json_path: str = JSON_LOG_PATH):
    """Guarda en JSON el evento consolidado con el tiempo total que la puerta estuvo abierta."""
    directorio = os.path.dirname(json_path)
    if directorio:
        os.makedirs(directorio, exist_ok=True)

    conf_promedio = round(sum(confianzas) / len(confianzas), 2) if confianzas else 0.0

    nuevo_registro = {
        "evento": "puerta_abierta",
        "hora_apertura": inicio_iso,
        "hora_cierre": fin_iso,
        "duracion_segundos": round(duracion, 2),
        "confianza_promedio": conf_promedio
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

    datos.append(nuevo_registro)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(datos, f, indent=4, ensure_ascii=False)

    print(f"\n[EVENTO REGISTRADO] Puerta abierta durante {nuevo_registro['duracion_segundos']}s -> Guardado en {json_path}\n")


def procesar_fuente(modelo: YOLO, fuente, target_class: str = TARGET_CLASS, conf_threshold: float = CONF_THRESHOLD):
    """Monitorea el video/cámara, calcula el tiempo transcurrido y registra el evento al cerrarse."""
    origen = str(fuente) if isinstance(fuente, Path) else fuente
    cap = cv2.VideoCapture(origen)

    if not cap.isOpened():
        raise RuntimeError(f"No se pudo abrir la fuente de video/cámara: {fuente}")

    target_normalizado = normalizar_texto(target_class)
    
    # Variables de control de estado
    puerta_abierta = False
    inicio_apertura_epoch = None
    inicio_apertura_iso = None
    ultimo_momento_detectada = None
    confianzas_acumuladas = []

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        resultados = modelo(frame, conf=conf_threshold, verbose=False)
        momento_actual = time.time()
        detectada_en_frame = False

        for r in resultados:
            for box in r.boxes:
                cls_id = int(box.cls[0])
                label_real = modelo.names[cls_id]
                conf = float(box.conf[0])

                if normalizar_texto(label_real) == target_normalizado:
                    detectada_en_frame = True
                    confianzas_acumuladas.append(conf)

        # Transición: La puerta se acaba de abrir
        if detectada_en_frame:
            ultimo_momento_detectada = momento_actual
            if not puerta_abierta:
                puerta_abierta = True
                inicio_apertura_epoch = momento_actual
                inicio_apertura_iso = datetime.now().isoformat(timespec='seconds')
                confianzas_acumuladas = [conf]
                print(f"[{inicio_apertura_iso}] Puerta detectada: ABIERTA")

        # Transición: La puerta se cerró (tras superar el margen de tolerancia)
        elif puerta_abierta:
            if (momento_actual - ultimo_momento_detectada) > TOLERANCIA_DESAPARICION_SEG:
                fin_apertura_iso = datetime.now().isoformat(timespec='seconds')
                duracion_total = ultimo_momento_detectada - inicio_apertura_epoch

                registrar_duracion(
                    inicio_iso=inicio_apertura_iso,
                    fin_iso=fin_apertura_iso,
                    duracion=duracion_total,
                    confianzas=confianzas_acumuladas
                )

                # Reset de estado
                puerta_abierta = False
                inicio_apertura_epoch = None
                inicio_apertura_iso = None
                confianzas_acumuladas = []

        # Mostrar duración en tiempo real sobre el video
        frame_mostrar = resultados[0].plot()
        if puerta_abierta and inicio_apertura_epoch:
            segundos_activa = int(momento_actual - inicio_apertura_epoch)
            cv2.putText(
                frame_mostrar,
                f"Abierta: {segundos_activa}s",
                (30, 50),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.0,
                (0, 0, 255),
                2
            )

        cv2.imshow("Monitoreo de Puerta", frame_mostrar)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Si el video termina con la puerta todavía abierta, cerrar y registrar el evento
    if puerta_abierta and inicio_apertura_epoch:
        fin_apertura_iso = datetime.now().isoformat(timespec='seconds')
        duracion_total = (ultimo_momento_detectada or time.time()) - inicio_apertura_epoch
        registrar_duracion(
            inicio_iso=inicio_apertura_iso,
            fin_iso=fin_apertura_iso,
            duracion=duracion_total,
            confianzas=confianzas_acumuladas
        )

    cap.release()
    cv2.destroyAllWindows()


def main():
    print("Iniciando monitoreo de tiempos de apertura...")

    if isinstance(VIDEO_PATH, Path) and not VIDEO_PATH.is_file():
        raise FileNotFoundError(f"No se encontró el archivo de entrada: {VIDEO_PATH}")

    modelo = YOLO(MODEL_PATH)

    procesar_fuente(
        modelo=modelo,
        fuente=VIDEO_PATH,
        target_class=TARGET_CLASS,
        conf_threshold=CONF_THRESHOLD
    )

    print(f"Monitoreo finalizado. Registros guardados en: {JSON_LOG_PATH}")


if __name__ == '__main__':
    main()