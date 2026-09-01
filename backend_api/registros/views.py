import subprocess
import sys
import os
from pathlib import Path

from django.conf import settings
from django.http import JsonResponse
from rest_framework import viewsets

from .models import EventoPuerta, Role, User, Warehouse, Zone, Camera, Door, Event, Logs
from .serializers import (EventoPuertaSerializer, RoleSerializer, UserSerializer, 
                            WarehouseSerializer, ZoneSerializer, CameraSerializer, 
                            DoorSerializer, EventSerializer, LogsSerializer)

# ==========================================
# VISTAS ANTERIORES (Demo de cámaras y Frontend)
# ==========================================
class EventoPuertaViewSet(viewsets.ModelViewSet):
    queryset = EventoPuerta.objects.all().order_by('-hora_apertura')
    serializer_class = EventoPuertaSerializer

def obtener_datos(request):
    datos = {
        "temperatura": -20.0,
        "estado_puerta": "cerrada"
    }
    return JsonResponse(datos)

# Los scripts de visión viven fuera de backend_api, en la raíz del proyecto.
# Se lanzan con esa raíz como cwd porque config.obtener_origen_video() devuelve
# rutas relativas (ej. "Videos/AndenPSP1.mp4").
RAIZ_PROYECTO = Path(settings.BASE_DIR).parent
DIR_SCRIPTS = RAIZ_PROYECTO / 'vision_worker' / 'scripts'


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

# ==========================================
# NUEVAS VISTAS (REST API Tablas Relacionales)
# ==========================================
class RoleViewSet(viewsets.ModelViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

class WarehouseViewSet(viewsets.ModelViewSet):
    queryset = Warehouse.objects.all()
    serializer_class = WarehouseSerializer

class ZoneViewSet(viewsets.ModelViewSet):
    queryset = Zone.objects.all()
    serializer_class = ZoneSerializer

class CameraViewSet(viewsets.ModelViewSet):
    queryset = Camera.objects.all()
    serializer_class = CameraSerializer

class DoorViewSet(viewsets.ModelViewSet):
    queryset = Door.objects.all()
    serializer_class = DoorSerializer

class EventViewSet(viewsets.ModelViewSet):
    queryset = Event.objects.all().order_by('-open_time')
    serializer_class = EventSerializer

class LogsViewSet(viewsets.ModelViewSet):
    queryset = Logs.objects.all()
    serializer_class = LogsSerializer