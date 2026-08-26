import subprocess
import sys
import os
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from rest_framework import viewsets
from .models import EventoPuerta
from .serializers import EventoPuertaSerializer

# [Tus vistas anteriores: EventoPuertaViewSet y dashboard_view se mantienen igual...]
class EventoPuertaViewSet(viewsets.ModelViewSet):
    queryset = EventoPuerta.objects.all().order_by('-hora_apertura')
    serializer_class = EventoPuertaSerializer

def dashboard_view(request):
    return render(request, 'dashboard.html')

def reportes_view(request):
    """Reporte general consolidado por cámara.

    Por ahora los datos los genera el frontend (reportes-datos.js) porque
    EventoPuerta todavía no tiene identidad de puerta y no hay de dónde
    agregarlos. Cuando exista el modelo Puerta, este es el lugar donde
    construir el consolidado y pasarlo por contexto.
    """
    return render(request, 'reportes.html')

# --- NUEVA VISTA PARA EJECUTAR YOLO ---
def ejecutar_script_modelo(request):
    script_path = os.path.join(settings.BASE_DIR, 'scripts', 'probar_modelo.py')
    try:
        # sys.executable asegura que se use el mismo entorno virtual que tiene instalado ultralytics y cv2
        subprocess.Popen([sys.executable, script_path], cwd=settings.BASE_DIR)
        return JsonResponse({"status": "ok", "message": "Modelo YOLO iniciado en segundo plano."})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)