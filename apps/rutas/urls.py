from django.urls import path
from . import views 

urlpatterns = [
    # Vista principal del mapa
    path('', views.mapa_view, name='mapa'),
    
    path('obtener-rutas-usuario/', views.obtener_rutas_user, name='obtener_rutas'),

    # Endpoint para calcular ruta óptima
    path('calcular-ruta/', views.calcular_ruta, name='calcular_ruta'),
]