from ..models import Camera
from ..serializers import CameraSerializer
from .base import BaseCrudViewSet


class CameraViewSet(BaseCrudViewSet):
    queryset = Camera.objects.select_related('rel_camera_zone').order_by('id')
    serializer_class = CameraSerializer
    search_fields = ['name', 'rel_camera_zone__name']

    def get_queryset(self):
        queryset = super().get_queryset()
        zone = self.request.query_params.get('zone')
        if zone:
            queryset = queryset.filter(rel_camera_zone=zone)
        return queryset
