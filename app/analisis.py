"""
Motor de analisis de puertas: deteccion YOLO + maquina de estados.

Aqui vive la logica que comparten los dos frentes que analizan la camara:

  * app/demo_analisis.py    -> demo manual, no toca el backend
  * app/analisis_en_vivo.py -> worker que arranca el boton "Analizar video"
                               del muro y publica los eventos en la API

Se separo del archivo de la demo para que el worker de produccion no tenga que
importar desde un modulo de demostracion: los dos consumen este.
"""
import os
from datetime import datetime

import cv2

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUTA_MODELO = os.path.join(BASE_DIR, "runs/detect/runs/detect/modelo_puerta_robusto/weights/best.pt")

UMBRAL_CONFIANZA = 0.55
SEGUNDOS_CONFIRMACION = 1.5  # cuánto debe sostenerse un cambio para darlo por cierto
SOLAPAMIENTO_MINIMO = 0.35   # cuánto de la caja debe caer dentro de la ROI
SEGUNDOS_ALERTA = 30         # puerta abierta más de esto = alerta
# El modelo actual confunde la cortina de PVC bajada con "puerta_medio_abierta"
# (0.96 de confianza sobre una puerta cerrada en esta camara). En modo estricto
# solo cuenta "puerta_abierta", que evita el falso positivo mientras no se
# reentrene con frames de esta camara.
CLASES_ABIERTA = {"puerta_abierta", "puerta_medio_abierta"}
CLASES_ABIERTA_ESTRICTO = {"puerta_abierta"}

# YOLO corre en CPU: 1080p tarda ~550 ms por frame y 640 px ~210 ms.
# Una puerta es un objeto grande, no necesita resolución completa.
IMGSZ_POR_DEFECTO = 640
FPS_ANALISIS_POR_DEFECTO = 4.0   # límite de ritmo, para no saturar la CPU

ANCHO_VENTANA, ALTO_VENTANA = 1024, 576
VERDE, ROJO, AMARILLO, BLANCO = (0, 200, 0), (0, 0, 255), (0, 200, 255), (255, 255, 255)

NOMBRE_ESCENA_COMPLETA = "Escena completa"


def hora():
    return datetime.now().strftime("%H:%M:%S")


class EstadoPuerta:
    """
    Máquina de estados de una puerta con anti-rebote.

    Un solo frame detectado no cambia el estado: la condición debe sostenerse
    SEGUNDOS_CONFIRMACION. Sin esto, una persona pasando delante de la puerta
    genera aperturas y cierres falsos.

    El anti-rebote se mide en segundos y no en frames a propósito: el ritmo de
    análisis varía con la carga de la CPU, y contar frames haría que el retardo
    de confirmación cambiara solo porque la máquina va más lenta.

    `publicador` es opcional (ver app/publicador_eventos.py): si se pasa, cada
    apertura y cierre confirmado se manda además a la API de Django. Sin él la
    clase se comporta igual que antes y solo acumula los eventos en memoria.
    """

    def __init__(self, nombre, publicador=None, segundos_alerta=SEGUNDOS_ALERTA):
        self.nombre = nombre
        self.publicador = publicador
        self.segundos_alerta = segundos_alerta
        self.estado = "cerrada"
        self.confianza = 0.0
        self.abierta_desde = None
        self.alerta_emitida = False
        self._cambio_desde = None   # instante en que la condición contraria empezó
        self._confianzas = []       # confianzas vistas en la apertura en curso
        self.eventos = []

    @property
    def segundos_abierta(self):
        return (datetime.now() - self.abierta_desde).total_seconds() if self.abierta_desde else 0.0

    @property
    def en_alerta(self):
        return self.estado == "abierta" and self.segundos_abierta >= self.segundos_alerta

    @property
    def confianza_promedio(self):
        """Promedio de confianza de la apertura en curso (0.0 si no hay ninguna)."""
        return sum(self._confianzas) / len(self._confianzas) if self._confianzas else 0.0

    def actualizar(self, detectada, confianza):
        self.confianza = confianza if detectada else 0.0
        ahora = datetime.now()
        contradice = detectada if self.estado == "cerrada" else not detectada

        if self.estado == "abierta" and detectada:
            self._confianzas.append(confianza)

        if not contradice:
            self._cambio_desde = None
        else:
            if self._cambio_desde is None:
                self._cambio_desde = ahora

            elif (ahora - self._cambio_desde).total_seconds() >= SEGUNDOS_CONFIRMACION:
                # El evento se fecha en el instante en que empezó a verse, no
                # cuando se confirmó: si no, cada duración perdería 1.5s.
                inicio_real = self._cambio_desde
                self._cambio_desde = None

                if self.estado == "cerrada":
                    self._confirmar_apertura(inicio_real, confianza)
                else:
                    self._confirmar_cierre(inicio_real)

        # Alerta de puerta abierta demasiado tiempo (una sola vez por apertura)
        if self.en_alerta and not self.alerta_emitida:
            self.alerta_emitida = True
            print(f"\n\033[91m  [ALERTA] {self.nombre} lleva {self.segundos_abierta:.0f}s abierta\033[0m\n")
            try:
                import winsound
                winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
            except Exception:
                pass

    def _confirmar_apertura(self, inicio_real, confianza):
        self.estado = "abierta"
        self.abierta_desde = inicio_real
        self.alerta_emitida = False
        self._confianzas = [confianza]
        print(f"  [{hora()}] {self.nombre}: APERTURA detectada (conf {confianza:.2f})")

        if self.publicador:
            self.publicador.abrir(self.nombre, inicio_real, confianza)

    def _confirmar_cierre(self, inicio_real):
        apertura = self.abierta_desde
        duracion = (inicio_real - apertura).total_seconds()
        promedio = self.confianza_promedio

        self.eventos.append({
            "puerta": self.nombre,
            "apertura": apertura.isoformat(),
            "cierre": inicio_real.isoformat(),
            "duracion_segundos": round(duracion, 1),
            "confianza_promedio": round(promedio, 2),
            "supero_umbral": duracion >= self.segundos_alerta,
        })
        self.estado = "cerrada"
        self.abierta_desde = None
        self.alerta_emitida = False
        self._confianzas = []
        print(f"  [{hora()}] {self.nombre}: CIERRE tras {duracion:.1f}s")

        if self.publicador:
            self.publicador.cerrar(self.nombre, apertura, inicio_real, duracion, promedio)

    def forzar_cierre(self, momento=None):
        """
        Cierra la apertura en curso, si hay, sin esperar la confirmacion.

        La usa el worker al terminar la sesion: si no, el ultimo evento se
        queda sin hora de cierre y la puerta figura abierta para siempre.
        """
        if not self.abierta_desde:
            return None
        self._confirmar_cierre(momento or datetime.now())
        return self.eventos[-1]

    def evento_en_curso(self):
        """
        La apertura que todavía no cerró, en el mismo formato que `eventos`.
        Retorna None si la puerta está cerrada.
        """
        if not self.abierta_desde:
            return None
        return {
            "puerta": self.nombre,
            "apertura": self.abierta_desde.isoformat(),
            "cierre": None,
            "duracion_segundos": round(self.segundos_abierta, 1),
            "confianza_promedio": round(self.confianza_promedio, 2),
            "supero_umbral": self.segundos_abierta >= self.segundos_alerta,
        }


def crear_estados(zonas, publicador=None, segundos_alerta=SEGUNDOS_ALERTA):
    """
    Una máquina de estados por zona. Sin ROIs definidas se trabaja sobre la
    escena completa, con una sola máquina.
    """
    nombres = [z.nombre for z in zonas] or [NOMBRE_ESCENA_COMPLETA]
    return {n: EstadoPuerta(n, publicador, segundos_alerta) for n in nombres}


def analizar_frame(modelo, frame, zonas, estados, imgsz=IMGSZ_POR_DEFECTO,
                   clases_abierta=CLASES_ABIERTA):
    """
    Corre YOLO sobre el frame y reparte las detecciones entre las zonas.
    Retorna las cajas dibujables [(caja, clase, confianza, nombre_zona)].
    """
    resultados = modelo(frame, imgsz=imgsz, conf=UMBRAL_CONFIANZA, verbose=False)

    detecciones = []
    for r in resultados:
        for box in r.boxes:
            nombre_clase = modelo.names[int(box.cls[0])]
            detecciones.append((box.xyxy[0].tolist(), nombre_clase, float(box.conf[0])))

    # Confianza máxima de "abierta" por zona
    confianza_por_zona = {nombre: 0.0 for nombre in estados}
    dibujables = []

    for caja, nombre_clase, conf in detecciones:
        if zonas:
            zona_asignada = None
            mejor = SOLAPAMIENTO_MINIMO
            for zona in zonas:
                solape = zona.fraccion_dentro(caja, frame.shape)
                if solape >= mejor:
                    mejor, zona_asignada = solape, zona.nombre
            if zona_asignada is None:
                continue   # detección fuera de toda ROI: se ignora
        else:
            zona_asignada = NOMBRE_ESCENA_COMPLETA

        if nombre_clase in clases_abierta:
            confianza_por_zona[zona_asignada] = max(confianza_por_zona[zona_asignada], conf)

        dibujables.append((caja, nombre_clase, conf, zona_asignada))

    for nombre, estado in estados.items():
        estado.actualizar(confianza_por_zona[nombre] > 0, confianza_por_zona[nombre])

    return dibujables


def dibujar(frame, zonas, estados, dibujables, fps, perdidos, clases_abierta=CLASES_ABIERTA):
    """Arma el frame de visualización a escala reducida."""
    forma_original = frame.shape
    vista = cv2.resize(frame, (ANCHO_VENTANA, ALTO_VENTANA))
    ex = ANCHO_VENTANA / forma_original[1]
    ey = ALTO_VENTANA / forma_original[0]

    for zona in zonas:
        activa = estados[zona.nombre].estado == "abierta"
        zona.dibujar(vista, escala_x=ex, escala_y=ey, activa=activa, forma_original=forma_original)

    for caja, nombre_clase, conf, _ in dibujables:
        x1, y1 = int(caja[0] * ex), int(caja[1] * ey)
        x2, y2 = int(caja[2] * ex), int(caja[3] * ey)
        color = ROJO if nombre_clase in clases_abierta else VERDE
        cv2.rectangle(vista, (x1, y1), (x2, y2), color, 2)
        cv2.putText(vista, f"{nombre_clase} {conf:.2f}", (x1, max(14, y1 - 6)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

    # Panel de estado
    cv2.rectangle(vista, (0, 0), (ANCHO_VENTANA, 30 + 26 * len(estados)), (0, 0, 0), -1)
    cv2.putText(vista, f"{hora()}  |  {fps:.1f} fps analisis  |  {perdidos} frames descartados",
                (12, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, BLANCO, 1)

    y = 46
    for estado in estados.values():
        if estado.estado == "abierta":
            color = ROJO if estado.en_alerta else AMARILLO
            texto = f"{estado.nombre}: ABIERTA  {estado.segundos_abierta:5.1f}s  (conf {estado.confianza:.2f})"
        else:
            color, texto = VERDE, f"{estado.nombre}: cerrada"
        cv2.putText(vista, texto, (12, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        y += 26

    return vista
