from .evento_puerta import EventoPuertaViewSet
from .role import RoleViewSet
from .user import UserViewSet
from .warehouse import WarehouseViewSet
from .zone import ZoneViewSet
from .camera import CameraViewSet
from .door import DoorViewSet
from .event import EventViewSet
from .logs import LogsViewSet
from .vision import obtener_datos, ejecutar_script_modelo, ejecutar_definir_roi

__all__ = [
    'EventoPuertaViewSet',  # Este se puede eliminar al insertar la base de datos
    'RoleViewSet',
    'UserViewSet',
    'WarehouseViewSet',
    'ZoneViewSet',
    'CameraViewSet',
    'DoorViewSet',
    'EventViewSet',
    'LogsViewSet',
    'obtener_datos',
    'ejecutar_script_modelo',
    'ejecutar_definir_roi',
]
