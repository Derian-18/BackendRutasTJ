from django.urls import path
from . import views 

urlpatterns = [
    # Autenticación
    path("login/", views.login_view, name="login"),
    path('dashboard/', views.administrador_view, name='administrador'),
    path('logout/', views.logout_view, name='logout'),

    # Registro administrador (flujo de 3 pasos con código por correo)
    path('registro/solicitar/', views.solicitar_codigo_view, name='solicitar_codigo'),
    path('registro/verificar/', views.verificar_codigo_view, name='verificar_codigo'),
    path('registro/crear/', views.crear_admin_view, name='crear_admin'),

    # Rutas
    path('guardar-ruta/', views.guardar_ruta, name='guardar_ruta'),
    path('obtener-rutas/', views.obtener_rutas, name='obtener_rutas'),
    path('eliminar-ruta/<int:ruta_id>/', views.eliminar_ruta, name='eliminar_ruta'),
]