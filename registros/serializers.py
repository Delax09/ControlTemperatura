from rest_framework import serializers
from .models import EventoPuerta

class EventoPuertaSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventoPuerta
        fields = '__all__'