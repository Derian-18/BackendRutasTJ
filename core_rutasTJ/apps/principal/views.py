from django.shortcuts import render, redirect
from django.core.mail import EmailMessage
from django.conf import settings
from django.contrib import messages
from django.template.loader import render_to_string

# =========================
# VISTAS BÁSICAS
# =========================

def home(request):
    return render(request, 'principal/index.html')

#def contacto(request):
#    if request.method == 'POST':
#        nombre = request.POST.get('nombre')
#        correo = request.POST.get('correo')
#        mensaje = request.POST.get('mensaje')
#
#        email_mensaje = f"""
#Nuevo mensaje de contacto:
#
#Nombre: {nombre}
#Correo: {correo}
#
#Mensaje:
#{mensaje}
#"""
#
#        try:
#            send_mail(
#                f'Contacto web - {nombre}',
#                email_mensaje,
#                settings.DEFAULT_FROM_EMAIL,
#                [config('EMAIL_RECIPENT')],
#                fail_silently=False,
#                reply_to=[correo]  # 👈 importante
#            )
#
#            messages.success(request, 'Mensaje enviado correctamente ✅')
#
#        except Exception as e:
#            print(f'Error al enviar: {e}')
#            messages.error(request, 'Error al enviar el mensaje ❌')
#
#        return redirect('contacto')
#
#    return render(request, 'principal/contacto.html')


def contacto(request):
    if request.method == "POST":
        nombre = request.POST.get('nombre')
        correo_usuario = request.POST.get('correo')
        mensaje_texto = request.POST.get('mensaje')

        # Construimos el cuerpo del mensaje usando un f-string
        # Esto mantiene el orden y se ve limpio en tu bandeja de entrada
        cuerpo_mensaje = (
            f"Has recibido un nuevo mensaje desde Rutas TJ\n"
            f"{'='*40}\n"
            f"Nombre: {nombre}\n"
            f"Correo: {correo_usuario}\n"
            f"{'='*40}\n\n"
            f"Mensaje:\n{mensaje_texto}\n\n"
            f"{'='*40}\n"
            f"Enviado desde el formulario de contacto oficial."
        )

        email = EmailMessage(
            subject=f"Consulta de {nombre} - Rutas TJ",
            body=cuerpo_mensaje,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=['jimenezderian81@gmail.com'], 
            reply_to=[correo_usuario], # Esto sigue siendo lo más importante
        )

        try:
            email.send()
            messages.success(request, "¡Mensaje enviado con éxito!")
            return redirect('contacto')
        except Exception as e:
            print(f"Error: {e}")
            messages.error(request, "Hubo un fallo al enviar. Revisa tu conexión.")

    return render(request, 'principal/contacto.html')