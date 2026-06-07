from django.db import models

# Create your models here.
# ESTO ES UN NODO
class Parada(models.Model):
    nombre = models.CharField(max_length=100)
    latitud = models.FloatField()
    longitud = models.FloatField()

class Ruta(models.Model):
    nombre = models.CharField(max_length=100)
    paradas = models.ManyToManyField(Parada)

# ESTO ES UNA ARISTA
class Conexion(models.Model):
    origen = models.ForeignKey(
        Parada,
        related_name="conexiones_salida",
        on_delete=models.CASCADE
    )
    destino = models.ForeignKey(
        Parada,
        related_name="conexiones_entrada",
        on_delete=models.CASCADE
    )
    distancia = models.FloatField()
    bidireccional = models.BooleanField(default=True)
    ruta = models.ForeignKey(Ruta, on_delete=models.CASCADE)