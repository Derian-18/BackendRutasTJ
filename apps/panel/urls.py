from django.urls import path
from . import views

urlpatterns = [
    # Autenticación
    path("login/", views.login_view, name="login"),
    path('dashboard/', views.administrador_view, name='administrador'),
    path('logout/', views.logout_view, name='logout'),

    # Registro administrador (3 pasos)
    path('registro/solicitar/', views.solicitar_codigo_view, name='solicitar_codigo'),
    path('registro/verificar/', views.verificar_codigo_view, name='verificar_codigo'),
    path('registro/crear/', views.crear_admin_view, name='crear_admin'),

    # Reset de contraseña (4 pasos)
    path('reset/', views.reset_solicitar_view, name='reset_solicitar'),
    path('reset/verificar/', views.reset_verificar_view, name='reset_verificar'),
    path('reset/usuario/', views.reset_elegir_usuario_view, name='reset_elegir_usuario'),
    path('reset/nueva/', views.reset_nueva_password_view, name='reset_nueva_password'),

    # Rutas
    path('guardar-ruta/', views.guardar_ruta, name='guardar_ruta'),
    path('obtener-rutas/', views.obtener_rutas, name='obtener_rutas'),
    path('eliminar-ruta/<int:ruta_id>/', views.eliminar_ruta, name='eliminar_ruta'),
]