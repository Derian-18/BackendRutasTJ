from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout as auth_logout
from django.contrib.auth.decorators import login_required, user_passes_test
from apps.principal.services import obtener_rutas_data
import json, math
from django.http import JsonResponse
from apps.principal.models import Ruta, Parada, Conexion
from django.db import transaction


# ==================== DISTANCIA ====================

def calcular_distancia(lat1, lon1, lat2, lon2):
    """Retorna distancia en METROS usando Haversine."""
    R = 6371000  # FIX: metros, no km (era R=6371 antes → distancias 1000x menores)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + \
        math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


# ==================== TRANSBORDO AUTOMÁTICO ====================

# Radio en metros para considerar que dos paradas son "la misma" y crear un transbordo
RADIO_TRANSBORDO = 50  # 50 metros

def buscar_parada_existente_cercana(lat, lon, radio=RADIO_TRANSBORDO):
    """
    Busca si ya existe una parada a menos de `radio` metros de (lat, lon).
    Si existe, la devuelve para reutilizarla como punto de transbordo.
    Si no, devuelve None para que se cree una parada nueva.
    """
    delta = radio / 111000

    candidatas = Parada.objects.filter(
        latitud__gte=lat - delta,
        latitud__lte=lat + delta,
        longitud__gte=lon - delta,
        longitud__lte=lon + delta,
    )

    mejor = None
    mejor_dist = float("inf")

    for p in candidatas:
        d = calcular_distancia(lat, lon, p.latitud, p.longitud)
        if d <= radio and d < mejor_dist:
            mejor_dist = d
            mejor = p

    return mejor


# ==================== AUTENTICACIÓN ====================

def login_view(request):
    if request.user.is_authenticated:
        return redirect('administrador')
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('administrador')
        else:
            messages.error(request, "Usuario o contraseña incorrectos")
    return render(request, 'panel/login.html')


def logout_view(request):
    auth_logout(request)
    messages.success(request, 'Sesión cerrada correctamente.')
    return redirect('home')


@login_required
def administrador_view(request):
    return render(request, 'panel/Administrador.html')


# ==================== RUTAS ====================

@login_required
def obtener_rutas(request):
    return JsonResponse(obtener_rutas_data(), safe=False)


@login_required
@csrf_exempt
def guardar_ruta(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, TypeError):
        return JsonResponse({'error': 'Body JSON inválido'}, status=400)

    nombre     = data.get('nombre')
    coordenadas = data.get('coordenadas')  # [[lat, lng], ...]

    if not nombre or not coordenadas or len(coordenadas) < 2:
        return JsonResponse({'error': 'Datos insuficientes para crear una ruta'}, status=400)

    try:
        with transaction.atomic():
            nueva_ruta     = Ruta.objects.create(nombre=nombre)
            paradas_creadas = []
            transbordos     = []  # Para informar al frontend qué paradas son transbordo

            for i, (lat, lng) in enumerate(coordenadas):

                # FIX: Antes de crear una parada nueva, buscar si ya existe una cercana.
                # Si existe → reutilizarla como punto de transbordo entre rutas.
                # Si no existe → crear una parada nueva normal.
                parada_existente = buscar_parada_existente_cercana(lat, lng)

                if parada_existente:
                    # Reutilizar parada existente → punto de transbordo
                    parada = parada_existente
                    transbordos.append({
                        "indice": i,
                        "nombre": parada.nombre,
                        "latitud": parada.latitud,
                        "longitud": parada.longitud,
                    })
                else:
                    # Crear parada nueva
                    parada = Parada.objects.create(
                        latitud=lat,
                        longitud=lng,
                        nombre=f"Parada en {lat:.4f}, {lng:.4f}"
                    )

                paradas_creadas.append(parada)

                # Crear conexión con la parada anterior
                if i > 0:
                    origen  = paradas_creadas[i - 1]
                    destino = paradas_creadas[i]
                    dist    = calcular_distancia(
                        origen.latitud, origen.longitud,
                        destino.latitud, destino.longitud
                    )
                    Conexion.objects.create(
                        origen=origen,
                        destino=destino,
                        distancia=dist,
                        ruta=nueva_ruta,
                        bidireccional=True
                    )

            # Asociar todas las paradas a la ruta
            nueva_ruta.paradas.set(paradas_creadas)

        respuesta = {
            'mensaje': 'Ruta, paradas y conexiones generadas con éxito',
            'id': nueva_ruta.id,
            'total_paradas': len(paradas_creadas),
            'transbordos_detectados': len(transbordos),
        }

        if transbordos:
            respuesta['transbordos'] = transbordos

        return JsonResponse(respuesta)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@user_passes_test(lambda u: u.is_staff, login_url='login')
def eliminar_ruta(request, ruta_id):
    if request.method == 'DELETE':
        try:
            ruta = Ruta.objects.get(id=ruta_id)
            ruta.delete()  # CASCADE elimina sus Conexiones automáticamente
            return JsonResponse({'success': True, 'message': 'Ruta eliminada correctamente'})
        except Ruta.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Ruta no encontrada'}, status=404)