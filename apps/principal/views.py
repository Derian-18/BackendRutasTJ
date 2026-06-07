from django.shortcuts import render, redirect
from django.core.mail import EmailMultiAlternatives  # <- Cambia EmailMessage por esto
from django.conf import settings
from django.contrib import messages

# =========================
# VISTAS BÁSICAS
# =========================

def home(request):
    return render(request, 'principal/index.html')

def contacto(request):
    if request.method == "POST":

        if request.POST.get('hp_field'):
            return redirect('contacto')

        nombre = request.POST.get('nombre')
        correo_usuario = request.POST.get('correo')
        mensaje_texto = request.POST.get('mensaje', '')[:3000]

        # Texto plano (fallback para clientes viejitos)
        cuerpo_plano = (
            f"Nombre: {nombre}\n"
            f"Correo: {correo_usuario}\n\n"
            f"Mensaje:\n{mensaje_texto}"
        )

        # HTML con diseño
        cuerpo_html = f"""
        <div style="margin:0;padding:0;background-color:#f4f6f9;font-family:Arial,sans-serif;">
          <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f4f6f9;padding:40px 0;">
            <tr><td align="center">
              <table width="580" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,0.08);">
                
                <!-- HEADER -->
                <tr>
                  <td style="background:linear-gradient(135deg,#1a73e8,#0d47a1);padding:30px 40px;text-align:center;">
                    <h1 style="margin:0;color:#fff;font-size:22px;">🚌 Rutas TJ</h1>
                    <p style="margin:6px 0 0;color:#bbdefb;font-size:13px;">Nuevo mensaje desde el formulario de contacto</p>
                  </td>
                </tr>

                <!-- DATOS DEL REMITENTE -->
                <tr>
                  <td style="padding:30px 40px 0;">
                    <p style="margin:0 0 6px;font-size:12px;color:#999;text-transform:uppercase;letter-spacing:1px;">Remitente</p>
                    <table width="100%" cellpadding="0" cellspacing="0" style="background:#f0f4ff;border-left:4px solid #1a73e8;border-radius:6px;">
                      <tr>
                        <td style="padding:16px 20px;">
                          <p style="margin:0 0 6px;font-size:16px;font-weight:bold;color:#222;">👤 {nombre}</p>
                          <p style="margin:0;font-size:14px;color:#1a73e8;">✉️ {correo_usuario}</p>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>

                <!-- MENSAJE -->
                <tr>
                  <td style="padding:24px 40px 30px;">
                    <p style="margin:0 0 8px;font-size:12px;color:#999;text-transform:uppercase;letter-spacing:1px;">Mensaje</p>
                    <div style="background:#fafafa;border:1px solid #e0e0e0;border-radius:8px;padding:18px 22px;">
                      <p style="margin:0;font-size:15px;color:#333;line-height:1.7;white-space:pre-wrap;">{mensaje_texto}</p>
                    </div>
                  </td>
                </tr>

                <!-- FOOTER -->
                <tr>
                  <td style="background:#f9f9f9;padding:16px 40px;text-align:center;border-top:1px solid #eee;">
                    <p style="margin:0;font-size:12px;color:#bbb;">Enviado desde el formulario oficial de <strong>Rutas TJ</strong></p>
                  </td>
                </tr>

              </table>
            </td></tr>
          </table>
        </div>
        """

        email = EmailMultiAlternatives(
            subject=f"Consulta de {nombre} - Rutas TJ",
            body=cuerpo_plano,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=['rutastj220@gmail.com'],
            reply_to=[correo_usuario],
        )
        email.attach_alternative(cuerpo_html, "text/html")  # <- Aquí se adjunta el HTML

        try:
            email.send()
            messages.success(request, "¡Mensaje enviado con éxito!")
            return redirect('contacto')
        except Exception as e:
            print(f"Error: {e}")
            messages.error(request, "Hubo un fallo al enviar. Revisa tu conexión.")

    return render(request, 'principal/contacto.html')