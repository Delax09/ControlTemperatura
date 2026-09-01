from .evento_puerta import EventoPuertaSerializer
from .role import RoleSerializer
from .user import UserSerializer
from .warehouse import WarehouseSerializer
from .zone import ZoneSerializer
from .camera import CameraSerializer
from .door import DoorSerializer
from .event import EventSerializer
from .logs import LogsSerializer

__all__ = [
    'EventoPuertaSerializer',  # Este se puede eliminar al insertar la base de datos
    'RoleSerializer',
    'UserSerializer',
    'WarehouseSerializer',
    'ZoneSerializer',
    'CameraSerializer',
    'DoorSerializer',
    'EventSerializer',
    'LogsSerializer',
]
