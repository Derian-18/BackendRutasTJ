from apps.principal.models import Parada, Ruta
from .busqueda_paradas import buscar_parada_con_expansion
from .algoritmo_rutas import dijkstra_con_transbordos


def calcular_ruta_optima(latA, lonA, latB, lonB):
    parada_inicio = buscar_parada_con_expansion(latA, lonA)
    parada_fin    = buscar_parada_con_expansion(latB, lonB)

    if not parada_inicio:
        return {"error": "No hay paradas cerca del origen"}
    if not parada_fin:
        return {"error": "No hay paradas cerca del destino"}

    camino = dijkstra_con_transbordos(parada_inicio.id, parada_fin.id)

    if not camino:
        return {"error": "No hay ruta disponible entre esos puntos"}

    return construir_respuesta(camino, parada_inicio, parada_fin)


def construir_respuesta(camino, parada_inicio, parada_fin):
    paradas_ids = [nodo for nodo, _ in camino]
    rutas_ids   = list({ruta for _, ruta in camino if ruta is not None})

    paradas_dict = {p.id: p for p in Parada.objects.filter(id__in=paradas_ids)}
    rutas_dict   = {r.id: r for r in Ruta.objects.filter(id__in=rutas_ids)}

    resultado    = []
    ruta_actual  = None
    tramo_virtual = False
    es_primer_nodo = True

    for nodo_id, ruta_id in camino:

        if ruta_id is None:
            # El nodo origen siempre llega con ruta=None (inicialización del
            # algoritmo), no es un transbordo a pie real.  Solo marcamos
            # tramo_virtual en nodos intermedios con ruta=None.
            if not es_primer_nodo:
                tramo_virtual = True

        else:
            tramo_virtual = False

            # FIX: solo emitir "transbordo" cuando la ruta realmente cambia
            # y no es la misma que ya estamos recorriendo.
            # Antes se emitía un transbordo por cada nodo donde ruta_id != ruta_actual,
            # lo que producía entradas repetidas cuando Dijkstra alternaba entre
            # dos rutas nodo a nodo (A→B→A→B...).
            if ruta_id != ruta_actual:
                # FIX adicional: si el último elemento del resultado ya es un
                # transbordo a esta misma ruta (puede ocurrir por aristas virtuales
                # consecutivas), no lo duplicamos.
                ultimo = resultado[-1] if resultado else None
                ya_esta = (
                    ultimo is not None
                    and ultimo.get("tipo") == "transbordo"
                    and ultimo.get("ruta") == rutas_dict[ruta_id].nombre
                )
                if not ya_esta:
                    resultado.append({
                        "tipo": "transbordo",
                        "ruta": rutas_dict[ruta_id].nombre,
                    })
                ruta_actual = ruta_id

        es_primer_nodo = False
        parada = paradas_dict.get(nodo_id)
        if parada:
            resultado.append({
                "tipo":     "parada",
                "id":       parada.id,
                "nombre":   parada.nombre,
                "latitud":  parada.latitud,
                "longitud": parada.longitud,
                "virtual":  tramo_virtual,
            })

    return {
        "origen": {
            "nombre":   parada_inicio.nombre,
            "latitud":  parada_inicio.latitud,
            "longitud": parada_inicio.longitud,
        },
        "destino": {
            "nombre":   parada_fin.nombre,
            "latitud":  parada_fin.latitud,
            "longitud": parada_fin.longitud,
        },
        "total_paradas":   len(paradas_ids),
        "ruta_optima":     resultado,
    }