from ..models import Warehouse
from ..serializers import WarehouseSerializer
from .base import BaseCrudViewSet


class WarehouseViewSet(BaseCrudViewSet):
    queryset = Warehouse.objects.all().order_by('id')
    serializer_class = WarehouseSerializer
    search_fields = ['name', 'address']
