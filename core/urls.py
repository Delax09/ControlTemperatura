from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter

# Importamos todas las vistas desde registros
from registros.views import (
    EventoPuertaViewSet, dashboard_view, reportes_view, ejecutar_script_modelo,
    RoleViewSet, UserViewSet, PlantViewSet, ZoneViewSet, 
    CameraViewSet, DoorViewSet, EventViewSet, LogsViewSet
)

router = DefaultRouter()

# --- Rutas de la API Anterior ---
router.register(r'eventos', EventoPuertaViewSet, basename='evento')

# --- Rutas de la API Nueva ---
router.register(r'roles', RoleViewSet)
router.register(r'users', UserViewSet)
router.register(r'plants', PlantViewSet)
router.register(r'zones', ZoneViewSet)
router.register(r'cameras', CameraViewSet)
router.register(r'doors', DoorViewSet)
router.register(r'events', EventViewSet) # Después eliminamos la ruta vieja de eventos
router.register(r'logs', LogsViewSet)

urlpatterns = [
    # Panel de Admin y Rutas API
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    
    # Rutas del Frontend y Scripts (Tus rutas anteriores)
    path('', dashboard_view, name='dashboard'),
    path('reportes/', reportes_view, name='reportes'),
    path('api/ejecutar-modelo/', ejecutar_script_modelo, name='ejecutar-modelo')
]

# Servir archivos de la carpeta alertas en desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)