from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter

# El frontend es un servidor aparte (Vite/React, ver frontend_app/). Django
# solo expone la API; aquí no se sirve ninguna plantilla.
from registros.views import (
    EventoPuertaViewSet, ejecutar_script_modelo, ejecutar_definir_roi,
    RoleViewSet, UserViewSet, WarehouseViewSet, ZoneViewSet,
    CameraViewSet, DoorViewSet, EventViewSet, LogsViewSet
)

router = DefaultRouter()

# --- Rutas de la API Anterior ---
router.register(r'eventos', EventoPuertaViewSet, basename='evento')

# --- Rutas de la API Nueva ---
router.register(r'roles', RoleViewSet)
router.register(r'users', UserViewSet)
router.register(r'warehouses', WarehouseViewSet)
router.register(r'zones', ZoneViewSet)
router.register(r'cameras', CameraViewSet)
router.register(r'doors', DoorViewSet)
router.register(r'events', EventViewSet) # Después eliminamos la ruta vieja de eventos
router.register(r'logs', LogsViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('api/ejecutar-modelo/', ejecutar_script_modelo, name='ejecutar-modelo'),
    path('api/definir-roi/', ejecutar_definir_roi, name='definir-roi'),
]

# Servir archivos de la carpeta alertas en desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
