from apps.principal.models import Parada
from apps.rutas.utils.geografia import distancia_metros
import math

# ==================== BÚSQUEDA DE PARADA CERCANA ====================

def parada_mas_cercana(lat, lon, radio):
    delta_lat = radio / 111000
    delta_lon = radio / (111000 * math.cos(math.radians(lat)))

    paradas_candidatas = Parada.objects.filter(
        latitud__gte=lat - delta_lat,
        latitud__lte=lat + delta_lat,
        longitud__gte=lon - delta_lon,
        longitud__lte=lon + delta_lon,
    )

    mejor_parada = None
    mejor_distancia = float("inf")

    for parada in paradas_candidatas:
        d = distancia_metros(lat, lon, parada.latitud, parada.longitud)
        if d <= radio and d < mejor_distancia:
            mejor_distancia = d
            mejor_parada = parada

    return mejor_parada

def buscar_parada_con_expansion(lat, lon):
    for radio in [800, 1200, 2000, 3000, 4000]: # Aqui podemos agregar diferentes radios de busquedas
        parada = parada_mas_cercana(lat, lon, radio)
        if parada:
            return parada
    return None