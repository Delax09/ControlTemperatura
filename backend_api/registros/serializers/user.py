from rest_framework import serializers

from ..models import User


class UserSerializer(serializers.ModelSerializer):
    """Lectura/escritura de usuarios. La contraseña nunca se devuelve."""

    role_name = serializers.CharField(source='role.role_name', read_only=True)

    class Meta:
        model = User
        fields = ['user_id', 'role', 'role_name', 'name', 'last_name', 'email', 'password']
        extra_kwargs = {'password': {'write_only': True}}
