import heapq
from .grafo_rutas import construir_grafo


# ==================== DIJKSTRA ====================
def dijkstra_con_transbordos(origen_id, destino_id, penalizacion_transbordo=500):

    if origen_id == destino_id:
        return [(origen_id, None)]

    grafo = construir_grafo()

    cola = [(0, origen_id, None)]
    distancias = {}
    padres = {}

    while cola:
        dist_actual, nodo_actual, ruta_actual = heapq.heappop(cola)
        estado = (nodo_actual, ruta_actual)

        if estado in distancias:
            continue

        distancias[estado] = dist_actual

        if nodo_actual == destino_id:
            break

        for vecino, peso, ruta_id in grafo.get(nodo_actual, []):
            penalizacion = 0
            if ruta_actual is not None and ruta_actual != ruta_id:
                penalizacion = penalizacion_transbordo

            nueva_dist = dist_actual + peso + penalizacion
            nuevo_estado = (vecino, ruta_id)

            if nuevo_estado not in distancias:
                padres[nuevo_estado] = estado
                heapq.heappush(cola, (nueva_dist, vecino, ruta_id))

    estados_finales = [e for e in distancias if e[0] == destino_id]

    if not estados_finales:
        return []

    estado_final = min(estados_finales, key=lambda e: distancias[e])

    camino = []
    actual = estado_final

    while actual in padres:
        nodo, ruta = actual
        camino.append((nodo, ruta))
        actual = padres[actual]

    nodo, ruta = actual
    camino.append((nodo, ruta))
    camino.reverse()

    return camino