from django.shortcuts import render
from apps.principal.models import Parada, Ruta, Conexion
import math, heapq, json
from django.http import JsonResponse


# =========================
# VISTAS BÁSICAS
# =========================

def home(request):
    return render(request, 'principal/index.html')

def contacto(request):
    return render(request, 'principal/contacto.html')


# =========================
# DISTANCIA SIMPLE
# =========================

def distancia_simple(lat1, lon1, lat2, lon2):
    return math.sqrt((lat1 - lat2)**2 + (lon1 - lon2)**2)


# =========================
# PARADA MÁS CERCANA
# =========================

def parada_mas_cercana(lat, lon):
    paradas = Parada.objects.all()
    mas_cercana = None
    min_dist = float('inf')

    for parada in paradas:
        d = distancia_simple(lat, lon, parada.latitud, parada.longitud)
        if d < min_dist:
            min_dist = d
            mas_cercana = parada

    return mas_cercana


# =========================
# DIJKSTRA CON RUTA Y PENALIZACIÓN DE TRANSBORDOS
# =========================

def dijkstra_con_transbordos(origen_id, destino_id):

    grafo = {}

    # Traemos también la ruta asociada
    conexiones = Conexion.objects.select_related("ruta")

    for conexion in conexiones:
        grafo.setdefault(conexion.origen.id, []).append(
            (conexion.destino.id, conexion.distancia, conexion.ruta.id)
        )

        if conexion.bidireccional:
            grafo.setdefault(conexion.destino.id, []).append(
                (conexion.origen.id, conexion.distancia, conexion.ruta.id)
            )

    # (distancia_acumulada, nodo_actual, ruta_actual)
    cola = [(0, origen_id, None)]
    distancias = {}
    padres = {}

    while cola:
        dist_actual, nodo_actual, ruta_actual = heapq.heappop(cola)

        if (nodo_actual, ruta_actual) in distancias:
            continue

        distancias[(nodo_actual, ruta_actual)] = dist_actual

        if nodo_actual == destino_id:
            break

        for vecino, peso, ruta_id in grafo.get(nodo_actual, []):

            penalizacion = 0

            # Penalizar si hay cambio de ruta
            if ruta_actual is not None and ruta_actual != ruta_id:
                penalizacion = 500  # Ajusta este valor si quieres más o menos castigo

            nueva_dist = dist_actual + peso + penalizacion

            estado_vecino = (vecino, ruta_id)

            if estado_vecino not in distancias:
                padres[estado_vecino] = (nodo_actual, ruta_actual)
                heapq.heappush(cola, (nueva_dist, vecino, ruta_id))

    # =========================
    # Reconstruir camino
    # =========================

    # Buscar el estado final con menor distancia
    estados_finales = [
        estado for estado in distancias
        if estado[0] == destino_id
    ]

    if not estados_finales:
        return []

    estado_final = min(estados_finales, key=lambda e: distancias[e])

    camino = []
    estado_actual = estado_final

    while estado_actual in padres:
        nodo, ruta = estado_actual
        camino.append({
            "parada": nodo,
            "ruta": ruta
        })
        estado_actual = padres[estado_actual]

    # Agregar origen
    nodo_origen, ruta_origen = estado_actual
    camino.append({
        "parada": nodo_origen,
        "ruta": ruta_origen
    })

    camino.reverse()
    return camino


# =========================
# VISTA PRINCIPAL
# =========================

def calcular_ruta(request):
    if request.method == 'POST':
        data = json.loads(request.body)

        latA = data.get('latA')
        lonA = data.get('lonA')
        latB = data.get('latB')
        lonB = data.get('lonB')

        parada_inicio = parada_mas_cercana(latA, lonA)
        parada_fin = parada_mas_cercana(latB, lonB)

        if not parada_inicio or not parada_fin:
            return JsonResponse({'error': 'No se encontraron paradas'}, status=400)

        camino = dijkstra_con_transbordos(parada_inicio.id, parada_fin.id)

        if not camino:
            return JsonResponse({'error': 'No se encontró ruta'}, status=400)

        resultado = []
        ruta_actual = None

        for paso in camino:
            parada = Parada.objects.get(id=paso["parada"])
            ruta_id = paso["ruta"]

            # Detectar transbordo
            if ruta_id != ruta_actual and ruta_id is not None:
                ruta_obj = Ruta.objects.get(id=ruta_id)
                resultado.append({
                    "tipo": "transbordo",
                    "ruta": ruta_obj.nombre
                })
                ruta_actual = ruta_id

            resultado.append({
                "tipo": "parada",
                "id": parada.id,
                "nombre": parada.nombre,
                "latitud": parada.latitud,
                "longitud": parada.longitud
            })

        return JsonResponse({
            "ruta_optima": resultado
        })