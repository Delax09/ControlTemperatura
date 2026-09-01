from rest_framework import serializers

from ..models import Camera


class CameraSerializer(serializers.ModelSerializer):
    zone_name = serializers.CharField(source='rel_camera_zone.name', read_only=True)

    class Meta:
        model = Camera
        fields = ['id', 'name', 'lock', 'rel_camera_zone', 'zone_name']
