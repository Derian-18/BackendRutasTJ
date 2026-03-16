from principal.models import Parada, Ruta
from services import buscar_parada_con_expansion, dijkstra_con_transbordos

def calcular_ruta_optima(latA, lonA, latB, lonB):
    parada_inicio = buscar_parada_con_expansion(latA, lonA)
    parada_fin = buscar_parada_con_expansion(latB, lonB)

    if not parada_inicio:
        return {"error": "No hay paradas cerca del origen"}

    if not parada_fin:
        return {"error": "No hay paradas cerca del destino"}

    camino = dijkstra_con_transbordos(parada_inicio.id, parada_fin.id)

    if not camino:
        return {"error": "No hay ruta disponible entre esos puntos"}

    return construir_respuesta(camino, parada_inicio, parada_fin)

# Def construir respuesta
def construir_respuesta(camino, parada_inicio, parada_fin):
    paradas_ids = [nodo for nodo, _ in camino]
    rutas_ids = list({ruta for _, ruta in camino if ruta is not None})

    paradas_dict = {p.id: p for p in Parada.objects.filter(id__in=paradas_ids)}
    rutas_dict = {r.id: r for r in Ruta.objects.filter(id__in=rutas_ids)}

    resultado = []
    ruta_actual = None

    for nodo_id, ruta_id in camino:

        if ruta_id is not None and ruta_id != ruta_actual:
            resultado.append({
                "tipo": "transbordo",
                "ruta": rutas_dict[ruta_id].nombre
            })
            ruta_actual = ruta_id

        parada = paradas_dict.get(nodo_id)

        if parada:
            resultado.append({
                "tipo": "parada",
                "id": parada.id,
                "nombre": parada.nombre,
                "latitud": parada.latitud,
                "longitud": parada.longitud
            })

    return {
        "origen": {
            "nombre": parada_inicio.nombre,
            "latitud": parada_inicio.latitud,
            "longitud": parada_inicio.longitud
        },
        "destino": {
            "nombre": parada_fin.nombre,
            "latitud": parada_fin.latitud,
            "longitud": parada_fin.longitud
        },
        "total_paradas": len(paradas_ids),
        "ruta_optima": resultado
    }