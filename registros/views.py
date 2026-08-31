import subprocess
import sys
import os
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
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

def dashboard_view(request):
    return render(request, 'dashboard.html')

def reportes_view(request):
    return render(request, 'reportes.html')

def ejecutar_script_modelo(request):
    script_path = os.path.join(settings.BASE_DIR, 'scripts', 'probar_modelo.py')
    try:
        subprocess.Popen([sys.executable, script_path], cwd=settings.BASE_DIR)
        return JsonResponse({"status": "ok", "message": "Modelo YOLO iniciado en segundo plano."})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)

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