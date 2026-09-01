from rest_framework import serializers

from ..models import EventoPuerta


class EventoPuertaSerializer(serializers.ModelSerializer):
    """Modelo de la demo de cámaras. Se elimina al migrar a las tablas nuevas."""

    class Meta:
        model = EventoPuerta
        fields = '__all__'
