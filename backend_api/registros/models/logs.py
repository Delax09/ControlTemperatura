#De momento veo como se guardan los logs
#preguntar antes de ejecutar algo 

from django.db import models

class Logs(models.Model):
    unique_id = models.AutoField(primary_key=True)
    foreign_key = models.IntegerField()
    fieldname = models.CharField(max_length=150)