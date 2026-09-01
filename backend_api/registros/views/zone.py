from ..models import Zone
from ..serializers import ZoneSerializer
from .base import BaseCrudViewSet


class ZoneViewSet(BaseCrudViewSet):
    queryset = Zone.objects.select_related('rel_zone_warehouse').order_by('id')
    serializer_class = ZoneSerializer
    search_fields = ['name', 'rel_zone_warehouse__name']

    def get_queryset(self):
        queryset = super().get_queryset()
        warehouse = self.request.query_params.get('warehouse')
        if warehouse:
            queryset = queryset.filter(rel_zone_warehouse=warehouse)
        return queryset
