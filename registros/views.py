from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets
from .models import EventoPuerta
from .serializers import EventoPuertaSerializer

class EventoPuertaViewSet(viewsets.ModelViewSet):
    queryset = EventoPuerta.objects.all().order_by('-hora_apertura')
    serializer_class = EventoPuertaSerializer