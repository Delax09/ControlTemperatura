from django.db import models
from .door import Door

class Event(models.Model):
    event_id = models.AutoField(primary_key=True)
    event_type = models.CharField(max_length=50)
    open_time = models.DateTimeField()
    close_time = models.DateTimeField(null=True, blank=True)
    temperature = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    rel_event_door = models.ForeignKey(Door, on_delete=models.CASCADE)

    def __str__(self):
        return f"Event {self.event_id} - Door {self.rel_event_door.id}"