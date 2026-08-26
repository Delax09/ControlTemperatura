import json
import os

import cv2
import numpy as np

# --- RUTAS ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUTA_ROIS = os.path.join(BASE_DIR, "config", "rois.json")

# Fracción mínima de la caja detectada que debe caer dentro de la zona
# para considerar que la detección pertenece a esa puerta.
SOLAPAMIENTO_MINIMO = 0.35


def clave_origen(origen_video):
    """
    Genera una clave estable para identificar el origen de video dentro del JSON.
    Un video local se identifica por su nombre de archivo; una cámara IP por su IP.
    """
    origen = str(origen_video)
    if origen.startswith("rtsp://"):
        # rtsp://usuario:password@ip:puerto/ruta -> ip
        sin_protocolo = origen.split("://", 1)[1]
        credenciales_y_host = sin_protocolo.split("/", 1)[0]
        host = credenciales_y_host.split("@")[-1]
        return f"camara_{host.split(':')[0]}"
    return os.path.basename(origen)


class ZonaPuerta:
    """
    Región de interés poligonal asociada a una puerta.

    Los puntos se guardan normalizados (0.0 - 1.0) para que la zona siga siendo
    válida aunque cambie la resolución del video o de la cámara.
    """

    def __init__(self, nombre, puntos_normalizados):
        self.nombre = nombre
        self.puntos_normalizados = [tuple(p) for p in puntos_normalizados]
        self._forma = None
        self._poligono = None
        self._mascara = None

    # --- Geometría ---
    def preparar(self, forma_frame):
        """Escala el polígono a la resolución del frame y cachea su máscara."""
        alto, ancho = forma_frame[:2]
        if self._forma == (alto, ancho):
            return

        self._forma = (alto, ancho)
        self._poligono = np.array(
            [(int(x * ancho), int(y * alto)) for x, y in self.puntos_normalizados],
            dtype=np.int32,
        )
        self._mascara = np.zeros((alto, ancho), dtype=np.uint8)
        cv2.fillPoly(self._mascara, [self._poligono], 255)

    def poligono(self, forma_frame):
        self.preparar(forma_frame)
        return self._poligono

    def fraccion_dentro(self, caja, forma_frame):
        """
        Retorna qué porcentaje (0.0 - 1.0) del área de la caja xyxy cae dentro
        de la zona. Es más robusto que evaluar sólo el centro del objeto.
        """
        self.preparar(forma_frame)
        alto, ancho = self._forma

        x1, y1, x2, y2 = (int(v) for v in caja)
        x1, x2 = max(0, min(x1, ancho - 1)), max(0, min(x2, ancho))
        y1, y2 = max(0, min(y1, alto - 1)), max(0, min(y2, alto))

        area_caja = (x2 - x1) * (y2 - y1)
        if area_caja <= 0:
            return 0.0

        recorte = self._mascara[y1:y2, x1:x2]
        return float(np.count_nonzero(recorte)) / float(area_caja)

    def contiene(self, caja, forma_frame, umbral=SOLAPAMIENTO_MINIMO):
        return self.fraccion_dentro(caja, forma_frame) >= umbral

    # --- Dibujo ---
    def dibujar(self, frame, escala_x=1.0, escala_y=1.0, activa=False, forma_original=None):
        """
        Dibuja la zona sobre el frame. Si el frame fue redimensionado para
        visualización, se pasan las escalas y la forma original del frame.
        """
        forma = forma_original if forma_original is not None else frame.shape
        puntos = self.poligono(forma).astype(np.float32).copy()
        puntos[:, 0] *= escala_x
        puntos[:, 1] *= escala_y
        puntos = puntos.astype(np.int32)

        color = (0, 0, 255) if activa else (0, 200, 255)

        # Relleno translúcido para no ocultar la imagen
        capa = frame.copy()
        cv2.fillPoly(capa, [puntos], color)
        cv2.addWeighted(capa, 0.20, frame, 0.80, 0, frame)
        cv2.polylines(frame, [puntos], True, color, 2)

        x, y = puntos[0]
        cv2.putText(
            frame, self.nombre, (int(x), max(20, int(y) - 8)),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2,
        )

    def a_dict(self):
        return {"nombre": self.nombre, "puntos": [list(p) for p in self.puntos_normalizados]}


def cargar_rois(origen_video):
    """
    Carga las zonas definidas para un origen de video.
    Retorna una lista vacía si no hay configuración (el sistema opera entonces
    sobre el frame completo, igual que antes).
    """
    if not os.path.exists(RUTA_ROIS):
        return []

    with open(RUTA_ROIS, "r", encoding="utf-8") as archivo:
        datos = json.load(archivo)

    zonas = datos.get(clave_origen(origen_video), [])
    return [ZonaPuerta(z["nombre"], z["puntos"]) for z in zonas]


def guardar_rois(origen_video, zonas):
    """Guarda (sobreescribiendo) las zonas de un origen de video."""
    os.makedirs(os.path.dirname(RUTA_ROIS), exist_ok=True)

    datos = {}
    if os.path.exists(RUTA_ROIS):
        with open(RUTA_ROIS, "r", encoding="utf-8") as archivo:
            datos = json.load(archivo)

    datos[clave_origen(origen_video)] = [z.a_dict() for z in zonas]

    with open(RUTA_ROIS, "w", encoding="utf-8") as archivo:
        json.dump(datos, archivo, indent=2, ensure_ascii=False)

    return RUTA_ROIS
