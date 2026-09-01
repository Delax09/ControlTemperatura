from rest_framework import serializers

from ..models import Door


class DoorSerializer(serializers.ModelSerializer):
    zone_name = serializers.CharField(source='rel_door_zone.name', read_only=True)
    camera_name = serializers.CharField(source='camera.name', read_only=True)

    class Meta:
        model = Door
        fields = ['door_id', 'name', 'roi', 'camera', 'camera_name',
                    'rel_door_zone', 'zone_name']
