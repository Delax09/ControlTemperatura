from ..models import Event
from ..serializers import EventSerializer
from .base import BaseCrudViewSet


class EventViewSet(BaseCrudViewSet):
    queryset = Event.objects.select_related('rel_event_door').order_by('-open_time')
    serializer_class = EventSerializer
    search_fields = ['event_type', 'rel_event_door__name']

    def get_queryset(self):
        """Filtros de la vista de reportes: puerta y rango de fechas."""
        queryset = super().get_queryset()
        params = self.request.query_params
        door = params.get('door')
        desde = params.get('desde')
        hasta = params.get('hasta')
        if door:
            queryset = queryset.filter(rel_event_door=door)
        if desde:
            queryset = queryset.filter(open_time__gte=desde)
        if hasta:
            queryset = queryset.filter(open_time__lte=hasta)
        return queryset
