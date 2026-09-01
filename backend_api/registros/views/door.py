from ..models import Door
from ..serializers import DoorSerializer
from .base import BaseCrudViewSet


class DoorViewSet(BaseCrudViewSet):
    queryset = Door.objects.select_related('camera', 'rel_door_zone').order_by('door_id')
    serializer_class = DoorSerializer
    search_fields = ['name', 'rel_door_zone__name', 'camera__name']

    def get_queryset(self):
        queryset = super().get_queryset()
        zone = self.request.query_params.get('zone')
        camera = self.request.query_params.get('camera')
        if zone:
            queryset = queryset.filter(rel_door_zone=zone)
        if camera:
            queryset = queryset.filter(camera=camera)
        return queryset
