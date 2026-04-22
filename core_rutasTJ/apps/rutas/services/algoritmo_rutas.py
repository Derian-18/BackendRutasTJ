import heapq
from .grafo_rutas import construir_grafo


# ==================== DIJKSTRA ====================
def dijkstra_con_transbordos(origen_id, destino_id, penalizacion_transbordo=500):

    if origen_id == destino_id:
        return [(origen_id, None)]

    grafo = construir_grafo()

    # Estado visitado: solo nodo_id.
    #
    # ANTES: el estado era (nodo_id, ruta_id), lo que permitía visitar el mismo
    # nodo múltiples veces con rutas distintas. Al reconstruir el camino esto
    # producía retrocesos (111→110→111→110...) que se traducían en decenas de
    # "transbordos" repetidos en el itinerario.
    #
    # AHORA: una vez que Dijkstra llega a un nodo por el camino más barato,
    # ese nodo queda cerrado. Guardamos qué ruta_id se usó al llegar para
    # poder calcular la penalización de transbordo correctamente.

    visitados: dict[int, None] = {}          # nodo_id → cerrado
    dist_nodo: dict[int, float] = {}         # nodo_id → mejor distancia conocida
    ruta_al_llegar: dict[int, int | None] = {}  # nodo_id → ruta con la que se llegó
    padres: dict[int, tuple[int, int | None]] = {}  # nodo_id → (nodo_padre, ruta_padre)

    contador = 0
    # (distancia, contador_desempate, nodo_id, ruta_id_actual)
    cola = [(0, contador, origen_id, None)]
    dist_nodo[origen_id] = 0
    ruta_al_llegar[origen_id] = None

    while cola:
        dist_actual, _, nodo_actual, ruta_actual = heapq.heappop(cola)

        if nodo_actual in visitados:
            continue

        visitados[nodo_actual] = None

        if nodo_actual == destino_id:
            break

        for vecino, peso, ruta_id in grafo.get(nodo_actual, []):
            if vecino in visitados:
                continue

            penalizacion = 0
            if ruta_actual is not None and ruta_id is not None and ruta_actual != ruta_id:
                penalizacion = penalizacion_transbordo

            nueva_dist = dist_actual + peso + penalizacion

            if nueva_dist < dist_nodo.get(vecino, float("inf")):
                dist_nodo[vecino] = nueva_dist
                ruta_al_llegar[vecino] = ruta_id
                padres[vecino] = (nodo_actual, ruta_actual)
                contador += 1
                heapq.heappush(cola, (nueva_dist, contador, vecino, ruta_id))

    if destino_id not in dist_nodo:
        return []

    # Reconstruir camino
    camino = []
    nodo = destino_id
    while nodo in padres:
        nodo_padre, ruta_padre = padres[nodo]
        camino.append((nodo, ruta_al_llegar[nodo]))
        nodo = nodo_padre
    camino.append((origen_id, ruta_al_llegar.get(origen_id)))
    camino.reverse()

    return camino