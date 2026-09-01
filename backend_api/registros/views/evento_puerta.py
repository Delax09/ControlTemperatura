from ..models import EventoPuerta
from ..serializers import EventoPuertaSerializer
from .base import BaseCrudViewSet


class EventoPuertaViewSet(BaseCrudViewSet):
    """CRUD de la demo de cámaras. Se elimina al migrar a la tabla Event."""

    queryset = EventoPuerta.objects.all().order_by('-hora_apertura')
    serializer_class = EventoPuertaSerializer
    search_fields = ['evento']
