from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout as auth_logout
from django.contrib.auth.decorators import login_required

# Create your views here.
# Aqui iran las vistas para el login

# Iniciar sesion
def login_view(request):
    if request.user.is_authenticated:
        return redirect('administrador')

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('administrador')  # Cambia a tu vista principal
        else:
            messages.error(request, "Usuario o contraseña incorrectos")

    return render(request, 'panel/login.html')

def logout_view(request):
    auth_logout(request)
    messages.success(request, 'Sesion cerrada correctamente.')
    return redirect('home')

@login_required
def administrador_view(request):
    return render(request, 'panel/Administrador.html')