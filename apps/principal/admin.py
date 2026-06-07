from django.contrib import admin
from .models import Ruta, Parada, Conexion

# Register your models here.
admin.site.register(Ruta)
admin.site.register(Parada)
admin.site.register(Conexion)