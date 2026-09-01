from ..models import Role
from ..serializers import RoleSerializer
from .base import BaseCrudViewSet


class RoleViewSet(BaseCrudViewSet):
    queryset = Role.objects.all().order_by('role_id')
    serializer_class = RoleSerializer
    search_fields = ['role_name']
