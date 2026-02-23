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

# Función auxiliar para calcular distancia (Haversine)
def calcular_distancia(lat1, lon1, lat2, lon2):
    radius = 6371  # Radio de la Tierra en km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) * math.sin(dlat / 2) + math.cos(math.radians(lat1)) \
        * math.cos(math.radians(lat2)) * math.sin(dlon / 2) * math.sin(dlon / 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return radius * c

# --- VISTAS DE AUTENTICACIÓN ---

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

# --- FUNCIONES DE LA APP ---

@login_required
def obtener_rutas(request):
    # Asegúrate de que obtener_rutas_data() devuelva una lista de diccionarios
    return JsonResponse(obtener_rutas_data(), safe=False)

@login_required
@csrf_exempt
def guardar_ruta(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            nombre = data.get('nombre')
            coordenadas = data.get('coordenadas') # Viene del mapa: [[lat, lng], ...]

            if not nombre or not coordenadas or len(coordenadas) < 2:
                return JsonResponse({'error': 'Datos insuficientes para crear una ruta'}, status=400)

            with transaction.atomic():
                # 1. Crear la Ruta
                nueva_ruta = Ruta.objects.create(nombre=nombre)
                
                paradas_creadas = []

                # 2. Procesar puntos para crear Paradas y Conexiones
                for i in range(len(coordenadas)):
                    lat, lng = coordenadas[i]
                    
                    # Buscamos si ya existe una parada en ese punto exacto o la creamos
                    parada, created = Parada.objects.get_or_create(
                        latitud=lat,
                        longitud=lng,
                        defaults={'nombre': f"Parada en {lat:.4f}, {lng:.4f}"}
                    )
                    paradas_creadas.append(parada)

                    # Si no es el primer punto, creamos la conexión con el anterior
                    if i > 0:
                        origen = paradas_creadas[i-1]
                        destino = paradas_creadas[i]
                        
                        dist = calcular_distancia(origen.latitud, origen.longitud, destino.latitud, destino.longitud)
                        
                        Conexion.objects.create(
                            origen=origen,
                            destino=destino,
                            distancia=dist,
                            ruta=nueva_ruta,
                            bidireccional=True # Por defecto según tu modelo
                        )

                # 3. Asociar todas las paradas a la ruta (ManyToManyField)
                nueva_ruta.paradas.set(paradas_creadas)

            return JsonResponse({
                'mensaje': 'Ruta, paradas y conexiones generadas con éxito',
                'id': nueva_ruta.id
            })

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@user_passes_test(lambda u: u.is_staff, login_url='login')
def eliminar_ruta(request, ruta_id):
    if request.method == 'DELETE':
        try:
            ruta = Ruta.objects.get(id=ruta_id)
            # Gracias al CASCADE en el modelo, esto borrará sus Conexiones automáticamente
            ruta.delete()
            return JsonResponse({'success': True, 'message': 'Ruta eliminada correctamente'})
        except Ruta.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Ruta no encontrada'}, status=404)