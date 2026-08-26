"""
Herramienta interactiva para definir las zonas de interés (ROI) de cada puerta.

Uso:
    python scripts/definir_roi.py

Controles:
    Click izquierdo  -> agregar punto al polígono en curso
    Click derecho    -> deshacer el último punto
    ENTER            -> cerrar el polígono y nombrarlo (por consola)
    d                -> eliminar la última zona guardada
    s                -> guardar todas las zonas en config/rois.json
    q / ESC          -> salir sin guardar
"""

import os
import sys

import cv2
import numpy as np

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import obtener_origen_video
from app.roi_config import ZonaPuerta, cargar_rois, guardar_rois

ANCHO_VENTANA = 1024
ALTO_VENTANA = 576
VENTANA = "Definir ROI de puertas"

puntos_en_curso = []


def al_hacer_click(evento, x, y, flags, parametros):
    if evento == cv2.EVENT_LBUTTONDOWN:
        puntos_en_curso.append((x, y))
    elif evento == cv2.EVENT_RBUTTONDOWN and puntos_en_curso:
        puntos_en_curso.pop()


def capturar_frame(origen):
    cap = cv2.VideoCapture(origen)
    if not cap.isOpened():
        print(f"No se pudo abrir el origen de video: {origen}")
        return None

    ret, frame = cap.read()
    cap.release()

    if not ret:
        print("No se pudo leer el primer frame del video.")
        return None
    return frame


def main():
    origen = obtener_origen_video()
    frame = capturar_frame(origen)
    if frame is None:
        return

    alto_original, ancho_original = frame.shape[:2]
    base = cv2.resize(frame, (ANCHO_VENTANA, ALTO_VENTANA))

    zonas = cargar_rois(origen)
    if zonas:
        print(f"Se cargaron {len(zonas)} zona(s) existente(s) para '{origen}'.")

    cv2.namedWindow(VENTANA)
    cv2.setMouseCallback(VENTANA, al_hacer_click)

    escala_x = ANCHO_VENTANA / ancho_original
    escala_y = ALTO_VENTANA / alto_original

    print(__doc__)

    while True:
        lienzo = base.copy()

        for zona in zonas:
            zona.dibujar(
                lienzo, escala_x, escala_y,
                forma_original=(alto_original, ancho_original),
            )

        # Polígono en construcción
        if puntos_en_curso:
            for punto in puntos_en_curso:
                cv2.circle(lienzo, punto, 4, (0, 255, 0), -1)
            if len(puntos_en_curso) > 1:
                cv2.polylines(
                    lienzo, [np.array(puntos_en_curso, dtype=np.int32)],
                    False, (0, 255, 0), 2,
                )

        cv2.putText(
            lienzo,
            f"Zonas: {len(zonas)} | puntos actuales: {len(puntos_en_curso)}",
            (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2,
        )
        cv2.putText(
            lienzo, "ENTER=cerrar zona  d=borrar ultima  s=guardar  q=salir",
            (20, ALTO_VENTANA - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1,
        )

        cv2.imshow(VENTANA, lienzo)
        tecla = cv2.waitKey(20) & 0xFF

        if tecla in (ord('q'), 27):
            print("Salida sin guardar.")
            break

        if tecla in (13, 10):  # ENTER
            if len(puntos_en_curso) < 3:
                print("Se necesitan al menos 3 puntos para cerrar una zona.")
                continue

            nombre = input("Nombre de la puerta (ej. Anden PSP 1): ").strip()
            if not nombre:
                nombre = f"Puerta {len(zonas) + 1}"

            # Normalizamos respecto a la resolución original del video
            normalizados = [
                (x / ANCHO_VENTANA, y / ALTO_VENTANA) for x, y in puntos_en_curso
            ]
            zonas.append(ZonaPuerta(nombre, normalizados))
            puntos_en_curso.clear()
            print(f"Zona '{nombre}' agregada.")

        elif tecla == ord('d') and zonas:
            eliminada = zonas.pop()
            print(f"Zona '{eliminada.nombre}' eliminada.")

        elif tecla == ord('s'):
            ruta = guardar_rois(origen, zonas)
            print(f"{len(zonas)} zona(s) guardada(s) en {ruta}")
            break

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
