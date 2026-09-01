"""
Lector de video en hilo aparte.

Con RTSP el problema no es abrir el stream, es el desfase: la camara empuja
frames a 15 fps y YOLO en 1080p procesa menos que eso. Si se lee en el mismo
bucle del analisis, el buffer se llena y terminas analizando imagen de hace
varios segundos. Aqui un hilo drena el stream continuamente y guarda solo el
ultimo frame, asi el analisis siempre trabaja sobre el presente.
"""
import threading
import time

import cv2

from app.config import USAR_CAMARA_IP


class LectorCamara:
    def __init__(self, origen, reconectar=True):
        self.origen = origen
        self.reconectar = reconectar and USAR_CAMARA_IP
        self.cap = None
        self._frame = None
        self._nuevo = False
        self._lock = threading.Lock()
        self._corriendo = False
        self._hilo = None
        self.frames_perdidos = 0   # frames que llegaron y nunca se analizaron
        self.desconexiones = 0

    def _abrir(self):
        cap = cv2.VideoCapture(self.origen, cv2.CAP_FFMPEG)
        if USAR_CAMARA_IP:
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 8000)
            cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 8000)
        return cap

    def iniciar(self):
        self.cap = self._abrir()
        if not self.cap.isOpened():
            raise ConnectionError(f"No se pudo abrir el origen de video: {self.origen}")

        self._corriendo = True
        self._hilo = threading.Thread(target=self._bucle, daemon=True)
        self._hilo.start()

        # Esperar el primer frame antes de devolver el control
        for _ in range(100):
            if self._frame is not None:
                break
            time.sleep(0.05)
        return self

    def _bucle(self):
        while self._corriendo:
            ok, frame = self.cap.read()

            if not ok:
                if not self.reconectar:
                    self._corriendo = False   # fin del archivo de video
                    break
                self.desconexiones += 1
                print(f"[CCTV] Stream caido, reconectando ({self.desconexiones})...")
                self.cap.release()
                time.sleep(3)
                self.cap = self._abrir()
                continue

            with self._lock:
                if self._nuevo:
                    # El frame anterior nunca se analizo: lo pisamos a proposito
                    self.frames_perdidos += 1
                self._frame = frame
                self._nuevo = True

    def leer(self):
        """Retorna (hay_frame_nuevo, frame). El frame es siempre el mas reciente."""
        with self._lock:
            if self._frame is None:
                return False, None
            frame, nuevo = self._frame, self._nuevo
            self._nuevo = False
        return nuevo, frame

    @property
    def activo(self):
        return self._corriendo

    def detener(self):
        self._corriendo = False
        if self._hilo:
            self._hilo.join(timeout=2)
        if self.cap:
            self.cap.release()

    def __enter__(self):
        return self.iniciar()

    def __exit__(self, *args):
        self.detener()
