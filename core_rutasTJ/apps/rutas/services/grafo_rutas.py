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

    FIX: Una parada puede pertenecer a MÚLTIPLES rutas (paradas compartidas).
    El código anterior usaba 'if parada_id not in parada_a_ruta' lo que
    asignaba cada parada a solo la primera ruta encontrada, dejando
    pares de rutas sin su arista de transbordo y forzando a Dijkstra
    a zigzaguear por aristas reales entre rutas → transbordos infinitos.

    Ahora se usa parada_a_rutas (plural): set de rutas por parada,
    y por_ruta acumula todas las paradas reales de cada ruta.
    """
    paradas_dict = {p.id: p for p in Parada.objects.only("id", "latitud", "longitud")}

    # FIX: una parada puede pertenecer a varias rutas → usamos set
    parada_a_rutas: dict[int, set[int]] = {}
    for c in Conexion.objects.only("origen_id", "destino_id", "ruta_id"):
        parada_a_rutas.setdefault(c.origen_id, set()).add(c.ruta_id)
        parada_a_rutas.setdefault(c.destino_id, set()).add(c.ruta_id)

    # Agrupar paradas por ruta (una parada puede aparecer en varios grupos)
    por_ruta: dict[int, list[int]] = {}
    for parada_id, rutas_ids in parada_a_rutas.items():
        for ruta_id in rutas_ids:
            por_ruta.setdefault(ruta_id, []).append(parada_id)

    rutas = list(por_ruta.keys())

    # Conjunto para evitar agregar la misma arista virtual dos veces
    aristas_virtuales_agregadas: set[tuple[int, int]] = set()

    for i in range(len(rutas)):
        for j in range(i + 1, len(rutas)):
            mejor_dist = float("inf")
            mejor_par = None

            for id_a in por_ruta[rutas[i]]:
                pa = paradas_dict.get(id_a)
                if not pa:
                    continue
                for id_b in por_ruta[rutas[j]]:
                    # FIX: si ambas paradas ya pertenecen a las mismas rutas
                    # (parada compartida) no hace falta arista virtual entre ellas
                    if parada_a_rutas[id_a] & parada_a_rutas[id_b]:
                        continue
                    pb = paradas_dict.get(id_b)
                    if not pb:
                        continue
                    d = distancia_metros(pa.latitud, pa.longitud, pb.latitud, pb.longitud)
                    if d <= RADIO_TRANSBORDO_VIRTUAL and d < mejor_dist:
                        mejor_dist = d
                        mejor_par = (id_a, id_b)

            if mejor_par:
                id_a, id_b = mejor_par
                par_ordenado = (min(id_a, id_b), max(id_a, id_b))
                if par_ordenado not in aristas_virtuales_agregadas:
                    aristas_virtuales_agregadas.add(par_ordenado)
                    grafo.setdefault(id_a, []).append((id_b, mejor_dist, None))
                    grafo.setdefault(id_b, []).append((id_a, mejor_dist, None))