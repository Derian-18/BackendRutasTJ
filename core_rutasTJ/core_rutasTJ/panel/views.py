from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout

# Create your views here.
# Aqui iran las vistas para el login

def home(request):
    return render(request, 'index.html')
# Iniciar sesion
def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect("index.html")  # Cambia a tu vista principal
        else:
            messages.error(request, "Usuario o contraseña incorrectos")

    return render(request, "login.html")

def contacto(request):
    return render(request, 'contacto.html')