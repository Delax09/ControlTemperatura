from django.db import models

class Warehouse(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=150)
    address = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name