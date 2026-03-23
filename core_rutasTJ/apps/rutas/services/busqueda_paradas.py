from apps.principal.models import Parada
from ..utils.geografia import distancia_metros

# ==================== BÚSQUEDA DE PARADA CERCANA ====================

def parada_mas_cercana(lat, lon, radio):
    delta = radio / 111000  # grados aproximados

    paradas_candidatas = Parada.objects.filter(
        latitud__gte=lat - delta,
        latitud__lte=lat + delta,
        longitud__gte=lon - delta,
        longitud__lte=lon + delta,
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
    for radio in [500, 800, 1200, 2000]:
        parada = parada_mas_cercana(lat, lon, radio)
        if parada:
            return parada
    return None