"""Vistas que no pertenecen a ninguna tabla: lanzan los scripts de visión."""

import os
import subprocess
import sys
from pathlib import Path

from django.conf import settings
from django.http import JsonResponse
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

# Los scripts de visión viven fuera de backend_api, en la raíz del proyecto.
# Se lanzan con esa raíz como cwd porque config.obtener_origen_video() devuelve
# rutas relativas (ej. "Videos/AndenPSP1.mp4").
RAIZ_PROYECTO = Path(settings.BASE_DIR).parent
DIR_SCRIPTS = RAIZ_PROYECTO / 'vision_worker' / 'scripts'

# El worker de análisis corre como proceso aparte, así que Django no comparte
# memoria con él: se comunican por los archivos de alertas/analisis/. Ese
# protocolo vive en app/estado_analisis.py, fuera de backend_api, y hay que
# poner la raíz del repo en el path para importarlo. Es un módulo liviano a
# propósito (sin cv2 ni ultralytics): importarlo no carga el modelo.
if str(RAIZ_PROYECTO) not in sys.path:
    sys.path.insert(0, str(RAIZ_PROYECTO))

from app.estado_analisis import (  # noqa: E402  (necesita el sys.path de arriba)
    analisis_vivos,
    esta_vivo,
    leer_estado,
    liberar,
    limpiar_detencion,
    pedir_detencion,
    reservar,
)

MODULO_ANALISIS = 'app.analisis_en_vivo'

VERDADEROS = ('1', 'true', 'si', 'sí', 'yes', 'on')


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


# --- Análisis en vivo (botón "Analizar video" de cada puerta) ---

def _pidio_ventana(request):
    """
    Si el muro pidió abrir el visor del video anotado.

    La ventana de OpenCV se abre en la máquina donde corre Django, no en el
    navegador: sirve para comprobar en el propio servidor que el modelo está
    encuadrando bien la puerta. Cerrarla no detiene el análisis.
    """
    valor = request.data.get('ventana', request.query_params.get('ventana'))
    return str(valor).strip().lower() in VERDADEROS

def _respuesta_estado(puerta_id, status='ok', message=''):
    """
    Forma única que consume el muro: `corriendo` + lo último que reportó el
    worker. Se devuelve igual al iniciar, al consultar y al detener, así el
    frontend tiene un solo contrato que leer.
    """
    estado = leer_estado(puerta_id)
    return Response({
        "status": status,
        "message": message,
        "puerta": str(puerta_id),
        "corriendo": esta_vivo(estado),
        "analisis": estado,
    })


@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def iniciar_analisis(request, puerta_id):
    """
    Arranca el análisis del video en tiempo real de la cámara de esta puerta.

    Se rechaza si ya hay un análisis vivo: hoy todas las puertas comparten un
    único origen de video (app/config.obtener_origen_video), y dos procesos
    leyéndolo duplicarían cada evento en la base.
    """
    vivos = analisis_vivos()

    if str(puerta_id) in vivos:
        return _respuesta_estado(puerta_id, 'ya_corriendo',
                                'El análisis de esta puerta ya está corriendo.')

    if vivos:
        otra = ', '.join(vivos)
        return _respuesta_estado(
            puerta_id, 'ocupado',
            f'Ya hay un análisis corriendo ({otra}) sobre la misma cámara. '
            'Deténlo antes de iniciar otro.',
        )

    # Si quedó una señal de detención sin consumir, el worker nuevo saldría
    # de inmediato.
    limpiar_detencion(puerta_id)

    # Se reserva el turno antes de lanzar: el worker tarda varios segundos en
    # importar sus dependencias y escribir su primer estado, y en esa ventana
    # una segunda pulsación levantaría otro proceso sobre la misma cámara.
    reservar(puerta_id)

    comando = [sys.executable, '-m', MODULO_ANALISIS, '--puerta', str(puerta_id)]
    if _pidio_ventana(request):
        comando.append('--ventana')

    opciones = {}
    if os.name == 'nt':
        # Consola propia: el worker vive más que el request y su log (aperturas,
        # cierres, reconexiones) tiene que quedar a la vista en el servidor.
        # Además evita que un reinicio del runserver se lo lleve consigo.
        opciones['creationflags'] = subprocess.CREATE_NEW_CONSOLE

    try:
        subprocess.Popen(comando, cwd=str(RAIZ_PROYECTO), **opciones)
    except Exception as error:
        liberar(puerta_id)   # no arrancó: la reserva no debe bloquear el próximo intento
        return Response(
            {
                "status": "error",
                "message": f'No se pudo iniciar el análisis: {error}',
                "puerta": str(puerta_id),
                "corriendo": False,
                "analisis": None,
            },
            status=500,
        )

    # El worker todavía está cargando YOLO y conectándose a la cámara: lo que
    # se devuelve es la reserva, en estado "iniciando". El muro lo ve corriendo
    # en firme cuando el worker empiece a latir.
    return _respuesta_estado(
        puerta_id, 'iniciado',
        'Análisis iniciado. Cargando el modelo y conectando a la cámara...',
    )


@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def estado_analisis(request, puerta_id):
    """Último estado reportado por el worker de esta puerta."""
    return _respuesta_estado(puerta_id)


@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def detener_analisis(request, puerta_id):
    """
    Pide al worker que termine.

    Se le avisa por archivo en vez de matarlo: así cierra la apertura que tenga
    en curso y no queda un evento sin hora de cierre en la base.
    """
    estado = leer_estado(puerta_id)
    if not esta_vivo(estado):
        return _respuesta_estado(puerta_id, 'no_corriendo',
                                 'No hay ningún análisis corriendo para esta puerta.')

    pedir_detencion(puerta_id)
    return _respuesta_estado(
        puerta_id, 'detencion_pedida',
        'Deteniendo el análisis: se está cerrando el evento en curso.',
    )
