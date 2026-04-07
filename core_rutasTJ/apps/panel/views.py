from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout as auth_logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required, user_passes_test
from apps.principal.services import obtener_rutas_data
import json, math, random, string
from django.http import JsonResponse
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Sum

from apps.principal.models import Ruta, Parada, Conexion
from django.db import transaction
from axes.models import AccessAttempt

from .models import CodigoRegistroAdmin
from .forms import VerificarCodigoForm, CrearAdminForm


# ==================== DISTANCIA ====================

def calcular_distancia(lat1, lon1, lat2, lon2):
    """Retorna distancia en METROS usando Haversine."""
    R = 6371000
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + \
        math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


# ==================== TRANSBORDO AUTOMÁTICO ====================

RADIO_TRANSBORDO = 50  # 50 metros

def buscar_parada_existente_cercana(lat, lon, radio=RADIO_TRANSBORDO):
    delta = radio / 111000
    candidatas = Parada.objects.filter(
        latitud__gte=lat - delta,
        latitud__lte=lat + delta,
        longitud__gte=lon - delta,
        longitud__lte=lon + delta,
    )
    mejor = None
    mejor_dist = float("inf")
    for p in candidatas:
        d = calcular_distancia(lat, lon, p.latitud, p.longitud)
        if d <= radio and d < mejor_dist:
            mejor_dist = d
            mejor = p
    return mejor


# ==================== AUTENTICACIÓN ====================

def login_view(request):
    if request.user.is_authenticated:
        return redirect('administrador')

    ip = request.META.get('REMOTE_ADDR')
    limit = getattr(settings, 'AXES_FAILURE_LIMIT', 3)

    total_fallos = AccessAttempt.objects.filter(
        ip_address=ip
    ).aggregate(total=Sum('failures_since_start'))['total'] or 0

    if total_fallos >= limit:
        return render(request, 'panel/bloqueado.html')

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('administrador')
        else:
            messages.error(request, "Usuario o contraseña incorrectos")

    return render(request, 'panel/login.html')


def logout_view(request):
    auth_logout(request)
    messages.success(request, 'Sesión cerrada correctamente.')
    return redirect('login')


@login_required
def administrador_view(request):
    return render(request, 'panel/Administrador.html')


# ==================== REGISTRO ADMINISTRADOR ====================

def _generar_codigo():
    """Genera un código numérico de 6 dígitos."""
    return ''.join(random.choices(string.digits, k=6))


def solicitar_codigo_view(request):
    """
    Paso 1: Se envía el código directamente al correo de empresa definido en settings.
    El usuario no necesita ingresar ningún correo.
    """
    if request.user.is_authenticated:
        return redirect('administrador')

    if request.method == "POST":
        correo_empresa = settings.ADMIN_EMPRESA_EMAIL

        # Invalidar códigos anteriores no usados
        CodigoRegistroAdmin.objects.filter(
            correo=correo_empresa,
            usado=False
        ).update(usado=True)

        # Crear nuevo código
        codigo = _generar_codigo()
        CodigoRegistroAdmin.objects.create(
            correo=correo_empresa,
            codigo=codigo
        )

        # Enviar correo via Brevo (SMTP)
        try:
            send_mail(
                subject="Código de registro administrador - Rutas TJ",
                message=(
                    f"Tu código de verificación para crear una cuenta administrador es:\n\n"
                    f"{codigo}\n\n"
                    f"Este código expira en 15 minutos.\n"
                    f"Si no solicitaste esto, ignora este mensaje."
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[correo_empresa],
                fail_silently=False,
            )
        except Exception:
            messages.error(request, "Hubo un error al enviar el correo. Intenta de nuevo.")
            return render(request, 'panel/solicitar_codigo.html')

        # Guardamos en sesión para el siguiente paso
        request.session['registro_correo'] = correo_empresa

        messages.success(request, "Código enviado. Revisa el correo de la empresa.")
        return redirect('verificar_codigo')

    return render(request, 'panel/solicitar_codigo.html')


def verificar_codigo_view(request):
    """
    Paso 2: El usuario ingresa el código que llegó al correo de empresa.
    """
    if request.user.is_authenticated:
        return redirect('administrador')

    correo = request.session.get('registro_correo')
    if not correo:
        return redirect('solicitar_codigo')

    form = VerificarCodigoForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        codigo_ingresado = form.cleaned_data['codigo'].strip()

        registro = CodigoRegistroAdmin.objects.filter(
            correo=correo,
            codigo=codigo_ingresado,
            usado=False
        ).order_by('-creado_en').first()

        if not registro or not registro.esta_vigente():
            messages.error(request, "Código inválido o expirado. Solicita uno nuevo.")
            return render(request, 'panel/verificar_codigo.html', {'form': form})

        # Código válido → marcar en sesión que puede proceder
        request.session['registro_verificado'] = True
        request.session['registro_codigo_id'] = registro.id

        return redirect('crear_admin')

    return render(request, 'panel/verificar_codigo.html', {'form': form})


def crear_admin_view(request):
    """
    Paso 3: Crear la cuenta administrador luego de verificar el código.
    """
    if request.user.is_authenticated:
        return redirect('administrador')

    if not request.session.get('registro_verificado'):
        return redirect('solicitar_codigo')

    correo    = request.session.get('registro_correo')
    codigo_id = request.session.get('registro_codigo_id')

    form = CrearAdminForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        # Doble check: el código sigue sin usarse
        try:
            registro = CodigoRegistroAdmin.objects.get(id=codigo_id, usado=False)
        except CodigoRegistroAdmin.DoesNotExist:
            messages.error(request, "El código ya fue utilizado. Solicita uno nuevo.")
            return redirect('solicitar_codigo')

        if not registro.esta_vigente():
            messages.error(request, "El código expiró. Solicita uno nuevo.")
            return redirect('solicitar_codigo')

        username = form.cleaned_data['username']
        password = form.cleaned_data['password1']

        User.objects.create_user(
            username=username,
            email=correo,
            password=password,
            is_staff=True,
        )

        # Marcar código como usado y limpiar sesión
        registro.usado = True
        registro.save()

        for key in ['registro_correo', 'registro_verificado', 'registro_codigo_id']:
            request.session.pop(key, None)

        messages.success(request, f"Cuenta '{username}' creada correctamente. Ya puedes iniciar sesión.")
        return redirect('login')

    return render(request, 'panel/crear_admin.html', {'form': form})


# ==================== RUTAS ====================

@login_required
def obtener_rutas(request):
    return JsonResponse(obtener_rutas_data(), safe=False)


@login_required
@csrf_exempt
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
                parada_existente = buscar_parada_existente_cercana(lat, lng)

                if parada_existente:
                    parada = parada_existente
                    transbordos.append({
                        "indice": i,
                        "nombre": parada.nombre,
                        "latitud": parada.latitud,
                        "longitud": parada.longitud,
                    })
                else:
                    parada = Parada.objects.create(
                        latitud=lat,
                        longitud=lng,
                        nombre=f"Parada en {lat:.4f}, {lng:.4f}"
                    )

                paradas_creadas.append(parada)

                if i > 0:
                    origen  = paradas_creadas[i - 1]
                    destino = paradas_creadas[i]
                    dist    = calcular_distancia(
                        origen.latitud, origen.longitud,
                        destino.latitud, destino.longitud
                    )
                    Conexion.objects.create(
                        origen=origen,
                        destino=destino,
                        distancia=dist,
                        ruta=nueva_ruta,
                        bidireccional=True
                    )

            nueva_ruta.paradas.set(paradas_creadas)

        respuesta = {
            'mensaje': 'Ruta, paradas y conexiones generadas con éxito',
            'id': nueva_ruta.id,
            'total_paradas': len(paradas_creadas),
            'transbordos_detectados': len(transbordos),
        }
        if transbordos:
            respuesta['transbordos'] = transbordos

        return JsonResponse(respuesta)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@user_passes_test(lambda u: u.is_staff, login_url='login')
def eliminar_ruta(request, ruta_id):
    if request.method == 'DELETE':
        try:
            ruta = Ruta.objects.get(id=ruta_id)
            ruta.delete()
            return JsonResponse({'success': True, 'message': 'Ruta eliminada correctamente'})
        except Ruta.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Ruta no encontrada'}, status=404)