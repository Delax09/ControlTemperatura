from rest_framework import serializers

from ..models import Zone


class ZoneSerializer(serializers.ModelSerializer):
    warehouse_name = serializers.CharField(source='rel_zone_warehouse.name', read_only=True)

    class Meta:
        model = Zone
        fields = ['id', 'name', 'rel_zone_warehouse', 'warehouse_name']
