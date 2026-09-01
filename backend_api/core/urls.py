from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

# El frontend es un servidor aparte (Vite/React, ver frontend_app/). Django
# solo expone la API; aquí no se sirve ninguna plantilla.
urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('registros.urls')),
]

# Servir archivos de la carpeta alertas en desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
