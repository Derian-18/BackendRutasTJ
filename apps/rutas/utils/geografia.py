# Este utils.py es para calculos matematicos
import math

R_TIERRA = 6371000  # radio de la tierra en metros


def distancia_metros(lat1, lon1, lat2, lon2):
    """
    Calcula la distancia entre dos coordenadas usando la fórmula de Haversine.
    Retorna la distancia en metros.
    """

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)

    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1)
        * math.cos(phi2)
        * math.sin(delta_lambda / 2) ** 2
    )

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R_TIERRA * c