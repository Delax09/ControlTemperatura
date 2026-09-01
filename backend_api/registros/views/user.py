from ..models import User
from ..serializers import UserSerializer
from .base import BaseCrudViewSet


class UserViewSet(BaseCrudViewSet):
    queryset = User.objects.select_related('role').order_by('user_id')
    serializer_class = UserSerializer
    search_fields = ['name', 'last_name', 'email']
