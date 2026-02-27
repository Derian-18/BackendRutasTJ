from django.shortcuts import render
from apps.principal.models import Parada, Ruta, Conexion
import math, heapq, json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

# Create your views here.
def mapa_view(request):
    return render(request, 'rutas/Mapa.html')

def distancia_metros(lat1, lon1, lat2, lon2):
    R = 6371000  # metros
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi/2)**2 + \
        math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def parada_mas_cercana(lat, lon, radio):

    # Aproximación en grados (1 grado ≈ 111km)
    delta = radio / 111000  

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

    radios = [500, 800, 1200, 2000]  # puedes ajustar

    for radio in radios:
        parada = parada_mas_cercana(lat, lon, radio)
        if parada:
            return parada

    return None

def dijkstra_con_transbordos(origen_id, destino_id, penalizacion_transbordo=500):

    # Construir grafo en memoria
    grafo = {}

    conexiones = Conexion.objects.select_related("ruta").only(
        "origen_id",
        "destino_id",
        "distancia",
        "bidireccional",
        "ruta_id"
    )

    for c in conexiones:
        grafo.setdefault(c.origen_id, []).append(
            (c.destino_id, c.distancia, c.ruta_id)
        )

        if c.bidireccional:
            grafo.setdefault(c.destino_id, []).append(
                (c.origen_id, c.distancia, c.ruta_id)
            )

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

    # Buscar mejor estado final
    estados_finales = [
        e for e in distancias if e[0] == destino_id
    ]

    if not estados_finales:
        return []

    estado_final = min(estados_finales, key=lambda e: distancias[e])

    # Reconstruir camino
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

def calcular_ruta(request):

    if request.method != "POST":
        return JsonResponse({"error": "Método no permitido"}, status=405)

    try:
        data = json.loads(request.body)

        latA = float(data.get("latA"))
        lonA = float(data.get("lonA"))
        latB = float(data.get("latB"))
        lonB = float(data.get("lonB"))

    except (TypeError, ValueError):
        return JsonResponse({"error": "Coordenadas inválidas"}, status=400)

    parada_inicio = buscar_parada_con_expansion(latA, lonA)
    parada_fin = buscar_parada_con_expansion(latB, lonB)

    if not parada_inicio or not parada_fin:
        return JsonResponse({"error": "No se encontraron paradas cercanas"}, status=404)

    camino = dijkstra_con_transbordos(parada_inicio.id, parada_fin.id)

    if not camino:
        return JsonResponse({"error": "No se encontró ruta disponible"}, status=404)

    # =========================
    # OPTIMIZACIÓN: precargar todo
    # =========================

    paradas_ids = [nodo for nodo, _ in camino]
    rutas_ids = list(set(
        ruta for _, ruta in camino if ruta is not None
    ))

    paradas_dict = {
        p.id: p for p in Parada.objects.filter(id__in=paradas_ids)
    }

    rutas_dict = {
        r.id: r for r in Ruta.objects.filter(id__in=rutas_ids)
    }

    resultado = []
    ruta_actual = None

    for nodo_id, ruta_id in camino:

        if ruta_id != ruta_actual and ruta_id is not None:
            resultado.append({
                "tipo": "transbordo",
                "ruta": rutas_dict[ruta_id].nombre
            })
            ruta_actual = ruta_id

        parada = paradas_dict[nodo_id]

        resultado.append({
            "tipo": "parada",
            "id": parada.id,
            "nombre": parada.nombre,
            "latitud": parada.latitud,
            "longitud": parada.longitud
        })

    return JsonResponse({
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
})