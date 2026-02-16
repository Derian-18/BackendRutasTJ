from django.urls import path
from . import views 

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path('admin/',  views.admin, name="admin"),
    path('mapa/', views.mapa_view, name='mapa'), 
]