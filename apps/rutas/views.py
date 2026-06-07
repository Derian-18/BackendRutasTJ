from django.shortcuts import render
import json
from django.http import JsonResponse
from apps.principal.services import obtener_rutas_data
from django.http import JsonResponse
from .services.ruta_services import calcular_ruta_optima

def mapa_view(request):
    return render(request, 'rutas/Mapa.html')

def obtener_rutas_user(request):
    return JsonResponse(obtener_rutas_data(), safe=False)

# ==================== VISTA PRINCIPAL ====================
def calcular_ruta(request):
    data = json.loads(request.body)

    resultado = calcular_ruta_optima(
        data["latA"],
        data["lonA"],
        data["latB"],
        data["lonB"]
    )

    return JsonResponse(resultado)