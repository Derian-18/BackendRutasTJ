from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib import messages
from django.core.mail import send_mail
from decouple import config

# =========================
# VISTAS BÁSICAS
# =========================

def home(request):
    return render(request, 'principal/index.html')

def contacto(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        correo = request.POST.get('correo')
        mensaje = request.POST.get('mensaje')

        email_mensaje = f"""
            Nuevo mensaje de contacto:

            Nombre: {nombre}
            Correo: {correo}
            Mensaje:
            {mensaje}
            """

        try:
            send_mail(
                f'Contacto web - {nombre}',
                email_mensaje,
                settings.EMAIL_HOST_USER,
                [config('EMAIL_RECIPENT')],
                fail_silently=False,
            )
            messages.success(request, 'Mensaje enviado correctamente ✅')
        except Exception as e:
            print(f'Error al enviar: {e}')
            messages.error(request, 'Error al enviar el mensaje ❌')

        return redirect('contacto')

    return render(request, 'principal/contacto.html')