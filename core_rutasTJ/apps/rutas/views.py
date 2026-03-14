from django.shortcuts import render
from apps.principal.models import Parada, Ruta, Conexion
import math, heapq, json, traceback
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from apps.principal.services import obtener_rutas_data


def mapa_view(request):
    return render(request, 'rutas/Mapa.html')

def obtener_rutas_user(request):
    return JsonResponse(obtener_rutas_data(), safe=False)


# ==================== HAVERSINE ====================

def distancia_metros(lat1, lon1, lat2, lon2):
    R = 6371000  # metros
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


# ==================== BÚSQUEDA DE PARADA CERCANA ====================

def parada_mas_cercana(lat, lon, radio):
    delta = radio / 111000  # grados aproximados

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
    for radio in [500, 800, 1200, 2000]:
        parada = parada_mas_cercana(lat, lon, radio)
        if parada:
            return parada
    return None


def buscar_paradas_cercanas_con_expansion(lat, lon, limite=6):
    radios = [500, 800, 1200, 2000]
    paradas_por_id = {}

    for radio in radios:
        delta = radio / 111000
        candidatas = Parada.objects.filter(
            latitud__gte=lat - delta,
            latitud__lte=lat + delta,
            longitud__gte=lon - delta,
            longitud__lte=lon + delta,
        )

        for parada in candidatas:
            d = distancia_metros(lat, lon, parada.latitud, parada.longitud)
            if d <= radio:
                distancia_actual = paradas_por_id.get(parada.id, (None, float("inf")))[1]
                if d < distancia_actual:
                    paradas_por_id[parada.id] = (parada, d)

    paradas_ordenadas = sorted(paradas_por_id.values(), key=lambda item: item[1])
    return paradas_ordenadas[:limite]


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


# ==================== DIJKSTRA ====================

def dijkstra_con_transbordos(origen_id, destino_id):

    if origen_id == destino_id:
        return [(origen_id, None)]

    grafo = construir_grafo()

    # Costo lexicográfico: primero minimizar transbordos, luego distancia.
    # Evita depender de una penalización fija que puede producir resultados
    # poco intuitivos cuando la red tiene tramos largos/cortos muy dispares.
    cola = [(0, 0, origen_id, None)]
    distancias = {}
    padres = {}

    while cola:
        transbordos_actuales, dist_actual, nodo_actual, ruta_actual = heapq.heappop(cola)
        estado = (nodo_actual, ruta_actual)

        if estado in distancias:
            continue

        distancias[estado] = (transbordos_actuales, dist_actual)

        if nodo_actual == destino_id:
            break

        for vecino, peso, ruta_id in grafo.get(nodo_actual, []):
            nuevos_transbordos = transbordos_actuales
            if ruta_actual is not None and ruta_actual != ruta_id:
                nuevos_transbordos += 1

            nueva_dist = dist_actual + peso
            nuevo_estado = (vecino, ruta_id)

            if nuevo_estado not in distancias:
                padres[nuevo_estado] = estado
                heapq.heappush(cola, (nuevos_transbordos, nueva_dist, vecino, ruta_id))

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


def contar_transbordos_camino(camino):
    ruta_anterior = None
    transbordos = 0

    for _, ruta_id in camino:
        if ruta_id is None:
            continue
        if ruta_anterior is None:
            ruta_anterior = ruta_id
            continue
        if ruta_id != ruta_anterior:
            transbordos += 1
            ruta_anterior = ruta_id

    return transbordos


# ==================== VISTA PRINCIPAL ====================

@csrf_exempt
def calcular_ruta(request):

    if request.method != "POST":
        return JsonResponse({"error": "Método no permitido"}, status=405)

    # Parsear body
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, TypeError):
        return JsonResponse({"error": "Body JSON inválido"}, status=400)

    # Validar coordenadas
    try:
        latA = float(data.get("latA"))
        lonA = float(data.get("lonA"))
        latB = float(data.get("latB"))
        lonB = float(data.get("lonB"))
    except (TypeError, ValueError):
        return JsonResponse({"error": "Coordenadas inválidas"}, status=400)

    if not (-90 <= latA <= 90 and -90 <= latB <= 90):
        return JsonResponse({"error": "Latitud fuera de rango"}, status=400)
    if not (-180 <= lonA <= 180 and -180 <= lonB <= 180):
        return JsonResponse({"error": "Longitud fuera de rango"}, status=400)

    # FIX: Todo el procesamiento dentro de try/except global.
    # Sin esto, cualquier excepción inesperada hace que Django devuelva
    # su propia página HTML de error, que el JS no puede parsear como JSON
    # y lo reporta como 404 o error genérico al azar.
    try:
        paradas_inicio_candidatas = buscar_paradas_cercanas_con_expansion(latA, lonA)
        paradas_fin_candidatas = buscar_paradas_cercanas_con_expansion(latB, lonB)

        # FIX: Usar 422 en vez de 404 para errores de lógica de negocio.
        # 404 significa "URL no encontrada" — confunde al JS y al developer.
        # 422 significa "datos válidos pero no se pudo procesar" — semánticamente correcto.
        if not paradas_inicio_candidatas:
            return JsonResponse(
                {"error": "No hay paradas dentro de 2km del origen. Haz clic más cerca de una ruta."},
                status=422
            )
        if not paradas_fin_candidatas:
            return JsonResponse(
                {"error": "No hay paradas dentro de 2km del destino. Haz clic más cerca de una ruta."},
                status=422
            )

        mejor = None
        mejor_camino = []
        parada_inicio = None
        parada_fin = None

        for p_inicio, dist_inicio in paradas_inicio_candidatas:
            for p_fin, dist_fin in paradas_fin_candidatas:
                camino_actual = dijkstra_con_transbordos(p_inicio.id, p_fin.id)
                if not camino_actual:
                    continue

                total_transbordos_camino = contar_transbordos_camino(camino_actual)
                # Se prioriza: 1) menos transbordos, 2) menor caminata total,
                # 3) menor número de saltos de paradas (desempate ligero).
                score = (
                    total_transbordos_camino,
                    round(dist_inicio + dist_fin, 2),
                    len(camino_actual),
                )

                if mejor is None or score < mejor:
                    mejor = score
                    mejor_camino = camino_actual
                    parada_inicio = p_inicio
                    parada_fin = p_fin

        if not mejor_camino:
            return JsonResponse(
                {"error": "No hay ruta disponible entre esos puntos."},
                status=422
            )

        camino = mejor_camino

        # Precargar en un solo query cada uno (evitar N+1)
        paradas_ids = [nodo for nodo, _ in camino]
        rutas_ids   = list({ruta for _, ruta in camino if ruta is not None})

        paradas_dict = {p.id: p for p in Parada.objects.filter(id__in=paradas_ids)}
        rutas_dict   = {r.id: r for r in Ruta.objects.filter(id__in=rutas_ids)}

        resultado   = []
        ruta_actual = None
        rutas_usadas = []

        for nodo_id, ruta_id in camino:
            if ruta_id is not None and ruta_id != ruta_actual:
                rutas_usadas.append(ruta_id)
                resultado.append({
                    "tipo": "transbordo",
                    "ruta": rutas_dict[ruta_id].nombre
                })
                ruta_actual = ruta_id

            parada = paradas_dict.get(nodo_id)
            if parada is None:
                continue

            resultado.append({
                "tipo":     "parada",
                "id":       parada.id,
                "nombre":   parada.nombre,
                "latitud":  parada.latitud,
                "longitud": parada.longitud
            })

        total_transbordos = max(0, len(rutas_usadas) - 1)

        return JsonResponse({
            "origen": {
                "nombre":   parada_inicio.nombre,
                "latitud":  parada_inicio.latitud,
                "longitud": parada_inicio.longitud
            },
            "destino": {
                "nombre":   parada_fin.nombre,
                "latitud":  parada_fin.latitud,
                "longitud": parada_fin.longitud
            },
            "requiere_transbordo": total_transbordos > 0,
            "total_transbordos": total_transbordos,
            "total_paradas": len(paradas_ids),
            "ruta_optima":   resultado
        })

    except Exception as e:
        # Imprimir traceback completo en la consola del servidor para debug
        traceback.print_exc()
        return JsonResponse({"error": f"Error interno: {str(e)}"}, status=500)
