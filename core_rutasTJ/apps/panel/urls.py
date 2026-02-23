from django.urls import path
from . import views 

urlpatterns = [
    # Autenticacion
    path("login/", views.login_view, name="login"),
    path('dashboard/', views.administrador_view, name='administrador'),
    path('logout/', views.logout_view, name='logout'),

    # Rutas
    path('guardar-ruta/', views.guardar_ruta, name='guardar_ruta'),
    path('obtener-rutas/', views.obtener_rutas, name='obtener_rutas'),
    path('eliminar-ruta/<int:ruta_id>/', views.eliminar_ruta, name='eliminar_ruta'),
]
