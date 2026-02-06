from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout

# Create your views here.
# Aqui iran las vistas para el login

def home(request):
    return render(request, 'index.html')

def panel_admin(request):
    return render(request, 'admin.html')

# Iniciar sesion
def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect("panel_admin")  # Cambia a tu vista principal
        else:
            messages.error(request, "Usuario o contraseña incorrectos")

    return render(request, "login.html")