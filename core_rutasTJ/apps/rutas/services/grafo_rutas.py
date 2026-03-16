from apps.principal.models import Conexion

# ==================== GRAFO ====================
def construir_grafo():
    grafo = {}
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
    return grafo