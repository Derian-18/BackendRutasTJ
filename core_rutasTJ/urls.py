"""
URL configuration for core_rutasTJ project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    # Esta es la url del admin
    path('admin/', admin.site.urls),

    # Aqui incluimos las urls de la app principal
    path('', include('apps.principal.urls')),

    # Aqui incluimos las urls de la app panel que es el administrador
    path('panel/', include('apps.panel.urls')),

    # Aqui incluimos las urls de la app rutas
    path('rutas/', include('apps.rutas.urls'))
]