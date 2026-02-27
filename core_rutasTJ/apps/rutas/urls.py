from django.urls import path
from . import views 

urlpatterns = [
    # Vista principal del mapa
    path('', views.mapa_view, name='mapa'),

    # Endpoint para calcular ruta óptima
    path('calcular-ruta/', views.calcular_ruta, name='calcular_ruta'),
]