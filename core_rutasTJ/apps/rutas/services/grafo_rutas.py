from apps.principal.models import Conexion, Parada
from ..utils.geografia import distancia_metros

# Distancia máxima en metros para considerar transbordo caminando entre paradas
RADIO_TRANSBORDO_VIRTUAL = 300  # metros

# ==================== GRAFO ====================
def construir_grafo():
    grafo = {}

    # 1. Conexiones reales definidas en la base de datos
    conexiones = Conexion.objects.only(
        "origen_id", "destino_id", "distancia", "bidireccional", "ruta_id"
    )
    for c in conexiones:
        grafo.setdefault(c.origen_id, []).append(
            (c.destino_id, c.distancia, c.ruta_id)
        )
        if c.bidireccional:
            grafo.setdefault(c.destino_id, []).append(
                (c.origen_id, c.distancia, c.ruta_id)
            )

    # 2. Conexiones virtuales: un solo transbordo por par de rutas
    agregar_transbordos_virtuales(grafo)

    return grafo


def agregar_transbordos_virtuales(grafo):
    """
    Por cada par de rutas, encuentra el par de paradas globalmente
    más cercano dentro del radio y agrega UNA SOLA arista virtual.
    Esto garantiza exactamente una línea naranja por transbordo.
    """
    paradas_dict = {p.id: p for p in Parada.objects.only("id", "latitud", "longitud")}

    # Determinar a qué ruta pertenece cada parada usando Conexion
    parada_a_ruta = {}
    for c in Conexion.objects.only("origen_id", "destino_id", "ruta_id"):
        if c.origen_id not in parada_a_ruta:
            parada_a_ruta[c.origen_id] = c.ruta_id
        if c.destino_id not in parada_a_ruta:
            parada_a_ruta[c.destino_id] = c.ruta_id

    # Agrupar paradas por ruta
    por_ruta = {}
    for parada_id, ruta_id in parada_a_ruta.items():
        por_ruta.setdefault(ruta_id, []).append(parada_id)

    rutas = list(por_ruta.keys())

    for i in range(len(rutas)):
        for j in range(i + 1, len(rutas)):
            # Buscar el par globalmente más cercano entre estas dos rutas
            mejor_dist = float("inf")
            mejor_par = None

            for id_a in por_ruta[rutas[i]]:
                pa = paradas_dict.get(id_a)
                if not pa:
                    continue
                for id_b in por_ruta[rutas[j]]:
                    pb = paradas_dict.get(id_b)
                    if not pb:
                        continue
                    d = distancia_metros(pa.latitud, pa.longitud, pb.latitud, pb.longitud)
                    if d <= RADIO_TRANSBORDO_VIRTUAL and d < mejor_dist:
                        mejor_dist = d
                        mejor_par = (id_a, id_b)

            # Agregar UNA SOLA arista virtual por par de rutas
            if mejor_par:
                id_a, id_b = mejor_par
                grafo.setdefault(id_a, []).append((id_b, mejor_dist, None))
                grafo.setdefault(id_b, []).append((id_a, mejor_dist, None))