from django.db import models

# Create your models here.

class EventoPuerta(models.Model):
    evento = models.CharField(max_length=50, default="puerta_abierta")
    hora_apertura = models.DateTimeField()
    hora_cierre = models.DateTimeField(null=True, blank=True)
    
    # Este campo se calculará automáticamente antes de guardar
    duracion_segundos = models.FloatField(null=True, blank=True)
    
    confianza_promedio = models.FloatField(help_text="Nivel de confianza de la detección del modelo")
    imagen = models.ImageField(upload_to='', null=True, blank=True)
    
    # NUEVO CAMPO: Temperatura ficticia (se actualizará con el sensor más adelante)
    temperatura = models.FloatField(null=True, blank=True, help_text="Temperatura registrada (en °C)")
    
    creado_el = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Calcular la duración automáticamente si tenemos ambas fechas
        if self.hora_apertura and self.hora_cierre:
            duracion = self.hora_cierre - self.hora_apertura
            # Se guarda el tiempo total en la columna duracion_segundos
            self.duracion_segundos = duracion.total_seconds()
            
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.evento} - {self.hora_apertura.strftime('%Y-%m-%d %H:%M:%S')} | Temp: {self.temperatura}°C"