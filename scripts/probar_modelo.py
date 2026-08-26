import cv2
import requests
import sys
import os
from datetime import datetime
from ultralytics import YOLO

# Añadir el directorio raíz al PATH para poder importar la carpeta 'app'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importar variables y funciones desde nuestro módulo de configuración
from app.config import API_URL, HEADERS_API, obtener_origen_video
from app.roi_config import SOLAPAMIENTO_MINIMO, ZonaPuerta, cargar_rois

# --- 1. INICIALIZACIÓN ---
RUTA_MODELO = "runs/detect/runs/detect/modelo_puerta_robusto-2/weights/best.pt"
CLASE_OBJETIVO = "puerta_abierta"
UMBRAL_CONFIANZA = 0.55

# Nº de frames consecutivos necesarios para confirmar un cambio de estado.
# Evita que un parpadeo del modelo genere eventos falsos en la API.
FRAMES_CONFIRMACION = 5

model = YOLO(RUTA_MODELO)
origen_video = obtener_origen_video()
cap = cv2.VideoCapture(origen_video)

# --- ZONAS DE INTERÉS (ROI) ---
zonas = cargar_rois(origen_video)
if not zonas:
    # Sin configuración de ROI se analiza el frame completo (comportamiento previo).
    zonas = [ZonaPuerta("Frame completo", [(0, 0), (1, 0), (1, 1), (0, 1)])]
    print("No hay ROI definidas. Ejecuta: python scripts/definir_roi.py")
else:
    print(f"ROI activas: {', '.join(z.nombre for z in zonas)}")


class SeguimientoPuerta:
    """Máquina de estados y ciclo de vida del evento para una puerta (una ROI)."""

    def __init__(self, zona):
        self.zona = zona
        self.estado = "cerrada"
        self.hora_apertura = None
        self.evento_id = None
        self.confianza = 0.0
        # Contadores de confirmación
        self.frames_abierta = 0
        self.frames_cerrada = 0

    # --- Lógica de estado ---
    def actualizar(self, detectada, confianza, frame):
        self.confianza = confianza if detectada else 0.0

        if detectada:
            self.frames_abierta += 1
            self.frames_cerrada = 0
        else:
            self.frames_cerrada += 1
            self.frames_abierta = 0

        if self.estado == "cerrada" and self.frames_abierta >= FRAMES_CONFIRMACION:
            self._abrir(confianza, frame)
        elif self.estado == "abierta" and self.frames_cerrada >= FRAMES_CONFIRMACION:
            self._cerrar()

    def _abrir(self, confianza, frame):
        self.estado = "abierta"
        self.hora_apertura = datetime.now()
        print(f"[{self.zona.nombre}] APERTURA {self.hora_apertura.strftime('%H:%M:%S')}")

        # Se envía solo el recorte de la ROI: la evidencia es más clara que el frame completo.
        recorte = self._recortar_zona(frame)
        ok, buffer = cv2.imencode('.jpg', recorte)
        if not ok:
            return

        datos = {
            "evento": "puerta_abierta",
            "hora_apertura": self.hora_apertura.isoformat(),
            "confianza_promedio": round(confianza, 2),
        }
        nombre_archivo = f"alerta_{self.hora_apertura.strftime('%Y%m%d_%H%M%S')}.jpg"
        archivos = {"imagen": (nombre_archivo, buffer.tobytes(), "image/jpeg")}

        try:
            res = requests.post(API_URL, data=datos, files=archivos, headers=HEADERS_API)
            if res.status_code == 201:
                self.evento_id = res.json().get('id')
        except Exception as e:
            print(f"Error conexión API: {e}")

    def _cerrar(self):
        self.estado = "cerrada"
        hora_cierre = datetime.now()

        if self.hora_apertura and self.evento_id:
            duracion = (hora_cierre - self.hora_apertura).total_seconds()
            print(f"[{self.zona.nombre}] CIERRE - abierta {duracion:.1f}s")
            datos_cierre = {
                "hora_cierre": hora_cierre.isoformat(),
                "duracion_segundos": round(duracion, 2),
            }
            try:
                requests.patch(f"{API_URL}{self.evento_id}/", data=datos_cierre, headers=HEADERS_API)
            except Exception:
                pass

        self.hora_apertura = None
        self.evento_id = None

    def _recortar_zona(self, frame):
        """Recorta el rectángulo que envuelve la ROI, con un margen de contexto."""
        poligono = self.zona.poligono(frame.shape)
        x, y, ancho, alto = cv2.boundingRect(poligono)
        margen = 20
        y1 = max(0, y - margen)
        y2 = min(frame.shape[0], y + alto + margen)
        x1 = max(0, x - margen)
        x2 = min(frame.shape[1], x + ancho + margen)
        recorte = frame[y1:y2, x1:x2]
        return recorte if recorte.size else frame

    @property
    def segundos_abierta(self):
        if self.estado == "abierta" and self.hora_apertura:
            return (datetime.now() - self.hora_apertura).total_seconds()
        return 0.0


seguimientos = [SeguimientoPuerta(zona) for zona in zonas]

print(f"Iniciando análisis. Origen de video: {origen_video}")

# --- 2. BUCLE PRINCIPAL DE INFERENCIA ---
while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        print("Error de lectura o fin de la transmisión. Intentando reconectar...")
        break

    resultados = model(frame, conf=UMBRAL_CONFIANZA, verbose=False)

    # Cajas de la clase objetivo detectadas en este frame
    detecciones = []
    for r in resultados:
        for box in r.boxes:
            if model.names[int(box.cls[0])] == CLASE_OBJETIVO:
                detecciones.append((box.xyxy[0], float(box.conf[0])))

    # --- 3. ASIGNACIÓN DE DETECCIONES A CADA ROI ---
    # Cada detección se atribuye a la zona con mayor solapamiento; así dos puertas
    # contiguas no se confunden entre sí.
    cajas_por_zona = {seguimiento.zona.nombre: [] for seguimiento in seguimientos}

    for caja, conf in detecciones:
        mejor_zona = None
        mejor_solapamiento = SOLAPAMIENTO_MINIMO

        for seguimiento in seguimientos:
            solapamiento = seguimiento.zona.fraccion_dentro(caja, frame.shape)
            if solapamiento >= mejor_solapamiento:
                mejor_solapamiento = solapamiento
                mejor_zona = seguimiento.zona.nombre

        if mejor_zona is not None:
            cajas_por_zona[mejor_zona].append((caja, conf))

    # --- 4. LÓGICA DE EVENTOS HACIA LA API (una por puerta) ---
    for seguimiento in seguimientos:
        cajas = cajas_por_zona[seguimiento.zona.nombre]
        confianza = max((c for _, c in cajas), default=0.0)
        seguimiento.actualizar(bool(cajas), confianza, frame)

    # --- 5. VISUALIZACIÓN ---
    frame_display = cv2.resize(frame, (1024, 576))
    escala_x = 1024 / frame.shape[1]
    escala_y = 576 / frame.shape[0]

    for seguimiento in seguimientos:
        seguimiento.zona.dibujar(
            frame_display, escala_x, escala_y,
            activa=(seguimiento.estado == "abierta"),
            forma_original=frame.shape,
        )

    # Cajas de detección ya filtradas por ROI
    for cajas in cajas_por_zona.values():
        for caja, _ in cajas:
            x1, y1, x2, y2 = map(int, caja)
            cv2.rectangle(
                frame_display,
                (int(x1 * escala_x), int(y1 * escala_y)),
                (int(x2 * escala_x), int(y2 * escala_y)),
                (0, 255, 0), 2,
            )

    # Panel de estado por puerta
    y_texto = 40
    for seguimiento in seguimientos:
        color = (0, 0, 255) if seguimiento.estado == "abierta" else (0, 255, 0)
        texto = f"{seguimiento.zona.nombre}: {seguimiento.estado.upper()} ({seguimiento.confianza:.2f})"
        if seguimiento.estado == "abierta":
            texto += f" {seguimiento.segundos_abierta:.1f}s"
        cv2.putText(frame_display, texto, (20, y_texto), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        y_texto += 32

    cv2.imshow("Monitor YOLO", frame_display)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
