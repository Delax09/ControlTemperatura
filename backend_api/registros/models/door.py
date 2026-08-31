from django.db import models
from .camera import Camera
from .zone import Zone

class Door(models.Model):
    door_id = models.AutoField(primary_key=True)
    camera = models.ForeignKey(Camera, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=100)
    roi = models.TextField(help_text="JSON format coordinates") #Coordenadas de la puerta en formato JSON

    rel_door_zone = models.ForeignKey(Zone, on_delete=models.CASCADE)

    def __str__(self):
        return self.name