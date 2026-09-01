from ..models import Logs
from ..serializers import LogsSerializer
from .base import BaseCrudViewSet


class LogsViewSet(BaseCrudViewSet):
    queryset = Logs.objects.all().order_by('-unique_id')
    serializer_class = LogsSerializer
    search_fields = ['fieldname']
