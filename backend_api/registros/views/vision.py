"""Vistas que no pertenecen a ninguna tabla: lanzan los scripts de visión."""

import os
import subprocess
import sys
from pathlib import Path

from django.conf import settings
from django.http import JsonResponse

# Los scripts de visión viven fuera de backend_api, en la raíz del proyecto.
# Se lanzan con esa raíz como cwd porque config.obtener_origen_video() devuelve
# rutas relativas (ej. "Videos/AndenPSP1.mp4").
RAIZ_PROYECTO = Path(settings.BASE_DIR).parent
DIR_SCRIPTS = RAIZ_PROYECTO / 'vision_worker' / 'scripts'


def obtener_datos(request):
    datos = {
        "temperatura": -20.0,
        "estado_puerta": "cerrada"
    }
    return JsonResponse(datos)


def _lanzar_script(nombre_archivo, consola_propia=False):
    """
    Arranca un script de visión en segundo plano y devuelve la respuesta JSON.

    `consola_propia` abre una ventana de consola nueva en Windows: la necesitan
    los scripts interactivos que piden datos por `input()`, porque el stdin del
    servidor Django no sirve para eso.
    """
    ruta = DIR_SCRIPTS / nombre_archivo
    if not ruta.is_file():
        return JsonResponse(
            {"status": "error", "message": f"No se encontró el script: {ruta}"},
            status=404,
        )

    opciones = {}
    if consola_propia and os.name == 'nt':
        opciones['creationflags'] = subprocess.CREATE_NEW_CONSOLE

    try:
        subprocess.Popen([sys.executable, str(ruta)], cwd=str(RAIZ_PROYECTO), **opciones)
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)

    return JsonResponse({"status": "ok", "message": f"{nombre_archivo} iniciado."})


def ejecutar_script_modelo(request):
    respuesta = _lanzar_script('probar_modelo.py')
    if respuesta.status_code == 200:
        return JsonResponse({"status": "ok", "message": "Modelo YOLO iniciado en segundo plano."})
    return respuesta


def ejecutar_definir_roi(request):
    """
    Abre la herramienta interactiva para dibujar las zonas (ROI) de las puertas.

    La ventana de OpenCV y su consola se abren en la máquina donde corre Django,
    no en el navegador del usuario.
    """
    respuesta = _lanzar_script('definir_roi.py', consola_propia=True)
    if respuesta.status_code == 200:
        return JsonResponse({
            "status": "ok",
            "message": "Herramienta de ROI abierta en el servidor.",
        })
    return respuesta
