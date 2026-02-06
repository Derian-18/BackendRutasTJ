from django.urls import path
from . import views 

urlpatterns = [
    path('', views.home, name='home'),
    path("login/", views.login_view, name="login"),
    path('panel_admin/', views.panel_admin, name="panel_admin")
]
