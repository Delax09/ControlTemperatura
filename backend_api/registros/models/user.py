from django.db import models
from .role import Role # Importamos el modelo Role

class User(models.Model):
    user_id = models.AutoField(primary_key=True)
    role = models.ForeignKey(Role, on_delete=models.RESTRICT)
    name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True, max_length=255)
    password = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.name} {self.last_name}"