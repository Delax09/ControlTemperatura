from django.db import models
from .zone import Zone # Importamos el modelo Zone

class Camera(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    lock = models.BooleanField(default=False)
    
    rel_camera_zone = models.ForeignKey(Zone, on_delete=models.SET_NULL, null=True, blank=True)
    


    def __str__(self):
        return self.name