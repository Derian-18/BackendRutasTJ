from django.shortcuts import render

# Create your views here.
def mapa_view(request):
    return render(request, 'rutas/Mapa.html')