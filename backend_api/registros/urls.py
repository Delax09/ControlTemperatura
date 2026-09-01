"""
Rutas de la app `registros`.

Una línea por tabla: el router de DRF genera el CRUD completo de cada módulo
(list, create, retrieve, update, partial_update, destroy).
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CameraViewSet,
    DoorViewSet,
    EventViewSet,
    EventoPuertaViewSet,
    LogsViewSet,
    RoleViewSet,
    UserViewSet,
    WarehouseViewSet,
    ZoneViewSet,
    ejecutar_definir_roi,
    ejecutar_script_modelo,
)

router = DefaultRouter()

# --- CRUD por tabla ---
router.register(r'roles', RoleViewSet)
router.register(r'users', UserViewSet)
router.register(r'warehouses', WarehouseViewSet)
router.register(r'zones', ZoneViewSet)
router.register(r'cameras', CameraViewSet)
router.register(r'doors', DoorViewSet)
router.register(r'events', EventViewSet)
router.register(r'logs', LogsViewSet)

# --- Ruta de la demo anterior (se elimina al migrar a `events`) ---
router.register(r'eventos', EventoPuertaViewSet, basename='evento')

urlpatterns = [
    path('', include(router.urls)),
    path('ejecutar-modelo/', ejecutar_script_modelo, name='ejecutar-modelo'),
    path('definir-roi/', ejecutar_definir_roi, name='definir-roi'),
]
