from rest_framework import serializers
from .models import EventoPuerta, Role, User, Warehouse, Zone, Camera, Door, Event, Logs

# --- SERIALIZADOR ANTERIOR ---
class EventoPuertaSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventoPuerta
        fields = '__all__'

# --- NUEVOS SERIALIZADORES ---
class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = '__all__'

class DoorSerializer(serializers.ModelSerializer):
    events = EventSerializer(source='event_set', many=True, read_only=True)
    class Meta:
        model = Door
        fields = '__all__'

class CameraSerializer(serializers.ModelSerializer):
    class Meta:
        model = Camera
        fields = '__all__'

class ZoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = Zone
        fields = '__all__'

class WarehouseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Warehouse
        fields = '__all__'

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['user_id', 'role', 'name', 'last_name', 'email']

class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = '__all__'

class LogsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Logs
        fields = '__all__'