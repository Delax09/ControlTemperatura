from django.db import models

# Create your models here.

class EventoPuerta(models.Model):
    evento = models.CharField(max_length=50, default="puerta_abierta")
    hora_apertura = models.DateTimeField()
    hora_cierre = models.DateTimeField(null=True, blank=True)
    duracion_segundos = models.FloatField(null=True, blank=True)
    confianza_promedio = models.FloatField()
    imagen = models.ImageField(upload_to='', null=True, blank=True)
    creado_el = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.evento} - {self.hora_apertura.strftime('%Y-%m-%d %H:%M:%S')}"
