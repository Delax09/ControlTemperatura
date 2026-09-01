from rest_framework import serializers

from ..models import Event


class EventSerializer(serializers.ModelSerializer):
    door_name = serializers.CharField(source='rel_event_door.name', read_only=True)
    duration_seconds = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = ['event_id', 'event_type', 'open_time', 'close_time',
                    'temperature', 'rel_event_door', 'door_name', 'duration_seconds']

    def get_duration_seconds(self, obj):
        if obj.open_time and obj.close_time:
            return (obj.close_time - obj.open_time).total_seconds()
        return None

    def validate(self, attrs):
        open_time = attrs.get('open_time', getattr(self.instance, 'open_time', None))
        close_time = attrs.get('close_time', getattr(self.instance, 'close_time', None))
        if open_time and close_time and close_time < open_time:
            raise serializers.ValidationError(
                {'close_time': 'La hora de cierre no puede ser anterior a la de apertura.'}
            )
        return attrs
