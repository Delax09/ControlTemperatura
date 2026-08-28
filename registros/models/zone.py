from django.db import models
from .warehouse import Warehouse # Importamos el modelo Warehouse

class Zone(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    
    rel_zone_warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE)

    def __str__(self):
        return self.name