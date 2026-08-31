from django.db import models

# --- MODELO ANTERIOR (Demo de cámaras) ---
class EventoPuerta(models.Model):
    evento = models.CharField(max_length=50, default="puerta_abierta")
    hora_apertura = models.DateTimeField()
    hora_cierre = models.DateTimeField(null=True, blank=True)
    duracion_segundos = models.FloatField(null=True, blank=True)
    confianza_promedio = models.FloatField(help_text="Nivel de confianza de la detección del modelo")
    imagen = models.ImageField(upload_to='', null=True, blank=True)
    temperatura = models.FloatField(null=True, blank=True, help_text="Temperatura registrada (en °C)")
    creado_el = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.hora_apertura and self.hora_cierre:
            duracion = self.hora_cierre - self.hora_apertura
            self.duracion_segundos = duracion.total_seconds()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.evento} - {self.hora_apertura.strftime('%Y-%m-%d %H:%M:%S')} | Temp: {self.temperatura}°C"


# --- NUEVOS MODELOS (Base de datos relacional) ---
class Role(models.Model):
    role_id = models.AutoField(primary_key=True)
    role_name = models.CharField(max_length=100)

    def __str__(self):
        return self.role_name

class User(models.Model):
    user_id = models.AutoField(primary_key=True)
    role = models.ForeignKey(Role, on_delete=models.RESTRICT)
    name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True, max_length=255)
    password = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.name} {self.last_name}"

class Warehouse(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=150)
    address = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class Zone(models.Model):
    zone_id = models.AutoField(primary_key=True)
    name_zone = models.CharField(max_length=100)
    id_warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE)

    def __str__(self):
        return self.name_zone

class Camera(models.Model):
    camera_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    zone = models.ForeignKey(Zone, on_delete=models.SET_NULL, null=True, blank=True)
    active = models.BooleanField(default=True)
    ip = models.CharField(max_length=50, blank=True, null=True)
    user = models.CharField(max_length=100, blank=True, null=True)
    password = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.name

class Door(models.Model):
    door_id = models.AutoField(primary_key=True)
    camera = models.ForeignKey(Camera, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=100)
    roi = models.TextField(help_text="JSON format coordinates")
    zone = models.ForeignKey(Zone, on_delete=models.CASCADE)

    def __str__(self):
        return self.name

class Event(models.Model):
    event_id = models.AutoField(primary_key=True)
    door = models.ForeignKey(Door, on_delete=models.CASCADE)
    event_type = models.CharField(max_length=50)
    open_time = models.DateTimeField()
    close_time = models.DateTimeField(null=True, blank=True)
    temperature = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return f"Event {self.event_id} - Door {self.door_id}"

class Logs(models.Model):
    unique_id = models.AutoField(primary_key=True)
    foreign_key = models.IntegerField()
    fieldname = models.CharField(max_length=150)