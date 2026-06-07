"""
panel/views.py

SOLID – SRP:
    Las vistas solo gestionan el ciclo HTTP (request → response).
    Toda la lógica de negocio está en services.py.

Seguridad:
    - csrf_exempt eliminado de los endpoints autenticados que modifican datos.
    - logout_view requiere POST para evitar logout CSRF via GET.
    - eliminar_ruta protegido con @login_required además de @user_passes_test.
"""

import json
import math

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout as auth_logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Sum
from django.http import JsonResponse
from django.shortcuts import render, redirect

from axes.models import AccessAttempt

from apps.principal.models import Ruta, Parada, Conexion
from apps.principal.services import obtener_rutas_data

from .forms import VerificarCodigoForm, CrearAdminForm, NuevaPasswordForm
from .models import CodigoVerificacion
from . import services


# ──────────────────────────────────────────────────────────────────────────────
# Utilidades geográficas (sin cambios de lógica, solo movidas aquí porque
# pertenecen al dominio de rutas; si crecen, moverlas a un geo_utils.py)
# ──────────────────────────────────────────────────────────────────────────────

def _calcular_distancia(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Fórmula de Haversine. Devuelve distancia en metros."""
    R = 6_371_000
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


RADIO_TRANSBORDO = 50  # metros


def _buscar_parada_cercana(lat: float, lon: float, radio: int = RADIO_TRANSBORDO):
    """Devuelve la parada existente más cercana dentro del radio, o None."""
    delta = radio / 111_000
    candidatas = Parada.objects.filter(
        latitud__gte=lat - delta, latitud__lte=lat + delta,
        longitud__gte=lon - delta, longitud__lte=lon + delta,
    )
    mejor, mejor_dist = None, float("inf")
    for p in candidatas:
        d = _calcular_distancia(lat, lon, p.latitud, p.longitud)
        if d <= radio and d < mejor_dist:
            mejor_dist, mejor = d, p
    return mejor


# ──────────────────────────────────────────────────────────────────────────────
# Autenticación
# ──────────────────────────────────────────────────────────────────────────────

def login_view(request):
    if request.user.is_authenticated:
        return redirect('administrador')

    ip = request.META.get('REMOTE_ADDR')
    limit = getattr(settings, 'AXES_FAILURE_LIMIT', 3)
    total_fallos = (
        AccessAttempt.objects.filter(ip_address=ip)
        .aggregate(total=Sum('failures_since_start'))['total'] or 0
    )

    if total_fallos >= limit:
        return render(request, 'panel/bloqueado.html')

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('administrador')
        messages.error(request, "Usuario o contraseña incorrectos.")

    return render(request, 'panel/login.html')


def logout_view(request):
    """
    FIX – Seguridad: solo acepta POST para evitar logout CSRF mediante
    un simple enlace GET enviado desde otro sitio.
    Actualiza el template para que el botón de logout use un <form method="post">.
    """
    if request.method == "POST":
        auth_logout(request)
        messages.success(request, 'Sesión cerrada correctamente.')
    return redirect('login')


@login_required
def administrador_view(request):
    return render(request, 'panel/Administrador.html')


# ──────────────────────────────────────────────────────────────────────────────
# Registro administrador (3 pasos)
# ──────────────────────────────────────────────────────────────────────────────

def solicitar_codigo_view(request):
    if request.user.is_authenticated:
        return redirect('administrador')

    if request.method == "POST":
        try:
            services.solicitar_codigo(CodigoVerificacion.Tipo.REGISTRO)
        except Exception:
            messages.error(request, "Hubo un error al enviar el correo. Intenta de nuevo.")
            return render(request, 'panel/solicitar_codigo.html')

        request.session['registro_correo'] = settings.ADMIN_EMPRESA_EMAIL
        messages.success(request, "Código enviado. Revisa el correo de la empresa.")
        return redirect('verificar_codigo')

    return render(request, 'panel/solicitar_codigo.html')


def verificar_codigo_view(request):
    if request.user.is_authenticated:
        return redirect('administrador')

    correo = request.session.get('registro_correo')
    if not correo:
        return redirect('solicitar_codigo')

    form = VerificarCodigoForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        codigo_ingresado = form.cleaned_data['codigo'].strip()
        registro = services.verificar_codigo(
            correo, codigo_ingresado, CodigoVerificacion.Tipo.REGISTRO
        )

        if not registro:
            messages.error(request, "Código inválido o expirado. Solicita uno nuevo.")
            return render(request, 'panel/verificar_codigo.html', {'form': form})

        request.session['registro_verificado'] = True
        request.session['registro_codigo_id']  = registro.id
        return redirect('crear_admin')

    return render(request, 'panel/verificar_codigo.html', {'form': form})


def crear_admin_view(request):
    if request.user.is_authenticated:
        return redirect('administrador')

    if not request.session.get('registro_verificado'):
        return redirect('solicitar_codigo')

    correo    = request.session.get('registro_correo')
    codigo_id = request.session.get('registro_codigo_id')
    form      = CrearAdminForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        try:
            user = services.crear_admin(
                codigo_id=codigo_id,
                username=form.cleaned_data['username'],
                password=form.cleaned_data['password1'],
                correo=correo,
            )
        except CodigoVerificacion.DoesNotExist:
            messages.error(request, "El código ya fue utilizado. Solicita uno nuevo.")
            return redirect('solicitar_codigo')
        except ValueError:
            messages.error(request, "El código expiró. Solicita uno nuevo.")
            return redirect('solicitar_codigo')

        for key in ('registro_correo', 'registro_verificado', 'registro_codigo_id'):
            request.session.pop(key, None)

        messages.success(request, f"Cuenta '{user.username}' creada correctamente. Ya puedes iniciar sesión.")
        return redirect('login')

    return render(request, 'panel/crear_admin.html', {'form': form})


# ──────────────────────────────────────────────────────────────────────────────
# Reset de contraseña (4 pasos)
# ──────────────────────────────────────────────────────────────────────────────

def reset_solicitar_view(request):
    """Paso 1: Envía el código al correo de empresa."""
    if request.user.is_authenticated:
        return redirect('administrador')

    if request.method == "POST":
        try:
            services.solicitar_codigo(CodigoVerificacion.Tipo.RESET)
        except Exception:
            messages.error(request, "Hubo un error al enviar el correo. Intenta de nuevo.")
            return render(request, 'panel/reset_solicitar.html')

        request.session['reset_correo'] = settings.ADMIN_EMPRESA_EMAIL
        messages.success(request, "Código enviado. Revisa el correo de la empresa.")
        return redirect('reset_verificar')

    return render(request, 'panel/reset_solicitar.html')


def reset_verificar_view(request):
    """Paso 2: Verifica el código."""
    if request.user.is_authenticated:
        return redirect('administrador')

    correo = request.session.get('reset_correo')
    if not correo:
        return redirect('reset_solicitar')

    form = VerificarCodigoForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        codigo_ingresado = form.cleaned_data['codigo'].strip()
        registro = services.verificar_codigo(
            correo, codigo_ingresado, CodigoVerificacion.Tipo.RESET
        )

        if not registro:
            messages.error(request, "Código inválido o expirado. Solicita uno nuevo.")
            return render(request, 'panel/reset_verificar.html', {'form': form})

        request.session['reset_verificado'] = True
        request.session['reset_codigo_id']  = registro.id
        return redirect('reset_elegir_usuario')

    return render(request, 'panel/reset_verificar.html', {'form': form})


def reset_elegir_usuario_view(request):
    """Paso 3: Elige el usuario cuya contraseña se reseteará."""
    if request.user.is_authenticated:
        return redirect('administrador')

    if not request.session.get('reset_verificado'):
        return redirect('reset_solicitar')

    codigo_id      = request.session.get('reset_codigo_id')
    usuarios_staff = User.objects.filter(is_staff=True).values_list('username', flat=True)

    if request.method == "POST":
        username_elegido = request.POST.get('username_reset', '').strip()

        if not username_elegido or not User.objects.filter(username=username_elegido, is_staff=True).exists():
            messages.error(request, "Selecciona un usuario válido.")
            return render(request, 'panel/reset_elegir_usuario.html', {'usuarios_staff': usuarios_staff})

        # Verificar que el código sigue vigente antes de avanzar al paso final
        try:
            registro = CodigoVerificacion.objects.get(
                id=codigo_id, tipo=CodigoVerificacion.Tipo.RESET, usado=False
            )
        except CodigoVerificacion.DoesNotExist:
            messages.error(request, "El código ya fue utilizado. Solicita uno nuevo.")
            return redirect('reset_solicitar')

        if not registro.esta_vigente():
            messages.error(request, "El código expiró. Solicita uno nuevo.")
            return redirect('reset_solicitar')

        request.session['reset_username'] = username_elegido
        return redirect('reset_nueva_password')

    return render(request, 'panel/reset_elegir_usuario.html', {'usuarios_staff': usuarios_staff})


def reset_nueva_password_view(request):
    """Paso 4: Establece la nueva contraseña."""
    if request.user.is_authenticated:
        return redirect('administrador')

    if not request.session.get('reset_verificado') or not request.session.get('reset_username'):
        return redirect('reset_solicitar')

    codigo_id = request.session.get('reset_codigo_id')
    username  = request.session.get('reset_username')
    form      = NuevaPasswordForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        try:
            services.resetear_password(
                codigo_id=codigo_id,
                username=username,
                nueva_password=form.cleaned_data['password1'],
            )
        except CodigoVerificacion.DoesNotExist:
            messages.error(request, "El código ya fue utilizado. Solicita uno nuevo.")
            return redirect('reset_solicitar')
        except ValueError:
            messages.error(request, "El código expiró. Solicita uno nuevo.")
            return redirect('reset_solicitar')
        except User.DoesNotExist:
            messages.error(request, "Usuario no encontrado.")
            return redirect('reset_solicitar')

        for key in ('reset_correo', 'reset_verificado', 'reset_codigo_id', 'reset_username'):
            request.session.pop(key, None)

        messages.success(request, f"Contraseña de '{username}' actualizada. Ya puedes iniciar sesión.")
        return redirect('login')

    return render(request, 'panel/reset_nueva_password.html', {'form': form, 'username': username})


# ──────────────────────────────────────────────────────────────────────────────
# Rutas
# ──────────────────────────────────────────────────────────────────────────────

@login_required
def obtener_rutas(request):
    return JsonResponse(obtener_rutas_data(), safe=False)


@login_required
# FIX – csrf_exempt eliminado: @login_required ya exige cookie de sesión,
# mantener CSRF activo protege contra peticiones forjadas entre sitios.
def guardar_ruta(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, TypeError):
        return JsonResponse({'error': 'Body JSON inválido'}, status=400)

    nombre      = data.get('nombre')
    coordenadas = data.get('coordenadas')

    if not nombre or not coordenadas or len(coordenadas) < 2:
        return JsonResponse({'error': 'Datos insuficientes para crear una ruta'}, status=400)

    try:
        with transaction.atomic():
            nueva_ruta      = Ruta.objects.create(nombre=nombre)
            paradas_creadas = []
            transbordos     = []

            for i, (lat, lng) in enumerate(coordenadas):
                parada_existente = _buscar_parada_cercana(lat, lng)

                if parada_existente:
                    parada = parada_existente
                    transbordos.append({
                        "indice":    i,
                        "nombre":   parada.nombre,
                        "latitud":  parada.latitud,
                        "longitud": parada.longitud,
                    })
                else:
                    parada = Parada.objects.create(
                        latitud=lat,
                        longitud=lng,
                        nombre=f"Parada en {lat:.4f}, {lng:.4f}",
                    )

                paradas_creadas.append(parada)

                if i > 0:
                    origen  = paradas_creadas[i - 1]
                    destino = paradas_creadas[i]
                    Conexion.objects.create(
                        origen=origen,
                        destino=destino,
                        distancia=_calcular_distancia(
                            origen.latitud, origen.longitud,
                            destino.latitud, destino.longitud,
                        ),
                        ruta=nueva_ruta,
                        bidireccional=True,
                    )

            nueva_ruta.paradas.set(paradas_creadas)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

    respuesta = {
        'mensaje':               'Ruta, paradas y conexiones generadas con éxito',
        'id':                    nueva_ruta.id,
        'total_paradas':         len(paradas_creadas),
        'transbordos_detectados': len(transbordos),
    }
    if transbordos:
        respuesta['transbordos'] = transbordos

    return JsonResponse(respuesta)


@login_required
@user_passes_test(lambda u: u.is_staff, login_url='login')
# FIX – csrf_exempt eliminado + @login_required añadido.
# user_passes_test solo evalúa el predicado pero no garantiza autenticación
# por sí solo cuando axes u otro middleware interviene.
def eliminar_ruta(request, ruta_id):
    if request.method != 'DELETE':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    try:
        ruta = Ruta.objects.get(id=ruta_id)
        ruta.delete()
        return JsonResponse({'success': True, 'message': 'Ruta eliminada correctamente'})
    except Ruta.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Ruta no encontrada'}, status=404)