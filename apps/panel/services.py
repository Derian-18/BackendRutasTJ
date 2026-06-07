"""
panel/services.py

SOLID – SRP (Single Responsibility Principle):
    Toda la lógica de negocio del panel de administración vive aquí.
    Las vistas solo se encargan de HTTP (recibir request, devolver response).

ACID – Atomicidad:
    Las operaciones que tocan múltiples tablas están envueltas en
    transaction.atomic() para garantizar que se completan por completo
    o se revierten por completo.
"""

from __future__ import annotations

import random
import string

from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.db import transaction

from .models import CodigoVerificacion


# ──────────────────────────────────────────────────────────────────────────────
# Helpers privados
# ──────────────────────────────────────────────────────────────────────────────

def _generar_codigo() -> str:
    """Genera un código OTP numérico de 6 dígitos."""
    return ''.join(random.choices(string.digits, k=6))


def _enviar_codigo(correo: str, asunto: str, cuerpo: str) -> None:
    """
    Envía un correo con el código OTP.
    Lanza excepción si el envío falla (fail_silently=False),
    permitiendo que el llamador maneje el error correctamente.
    """
    send_mail(
        subject=asunto,
        message=cuerpo,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[correo],
        fail_silently=False,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Códigos OTP – Registro y Reset
# ──────────────────────────────────────────────────────────────────────────────

def solicitar_codigo(tipo: str) -> None:
    """
    Genera un nuevo código OTP para el correo de empresa del tipo indicado
    (CodigoVerificacion.Tipo.REGISTRO o .RESET) y lo envía por correo.

    ACID – Atomicidad:
        La invalidación de códigos anteriores y la creación del nuevo ocurren
        dentro de una transacción.  El correo se envía FUERA de la transacción
        para que, si falla, el registro creado se revierta y no quede un código
        "huérfano" en la base de datos que nunca llegó al destinatario.

    Raises:
        Exception: cualquier error de envío de correo para que la vista
                   pueda mostrar el mensaje adecuado al usuario.
    """
    correo_empresa = settings.ADMIN_EMPRESA_EMAIL
    codigo = _generar_codigo()

    # --- Bloque atómico: invalidar anteriores y crear el nuevo ---
    # El código se crea primero; si el correo falla hacemos rollback manual.
    with transaction.atomic():
        CodigoVerificacion.objects.filter(
            correo=correo_empresa, tipo=tipo, usado=False
        ).update(usado=True)

        registro = CodigoVerificacion.objects.create(
            correo=correo_empresa,
            codigo=codigo,
            tipo=tipo,
        )

    # --- Envío fuera de la transacción ---
    # Si falla, marcamos el registro recién creado como usado para dejarlo inerte.
    asuntos = {
        CodigoVerificacion.Tipo.REGISTRO: "Código de registro administrador - Rutas TJ",
        CodigoVerificacion.Tipo.RESET:    "Código para restablecer contraseña - Rutas TJ",
    }
    cuerpos = {
        CodigoVerificacion.Tipo.REGISTRO: (
            f"Tu código de verificación para crear una cuenta administrador es:\n\n"
            f"{codigo}\n\n"
            f"Este código expira en 15 minutos.\n"
            f"Si no solicitaste esto, ignora este mensaje."
        ),
        CodigoVerificacion.Tipo.RESET: (
            f"Tu código para restablecer la contraseña es:\n\n"
            f"{codigo}\n\n"
            f"Este código expira en 15 minutos.\n"
            f"Si no solicitaste esto, ignora este mensaje."
        ),
    }

    try:
        _enviar_codigo(
            correo=correo_empresa,
            asunto=asuntos[tipo],
            cuerpo=cuerpos[tipo],
        )
    except Exception:
        # Revertir: marcar el código como usado para que no pueda emplearse
        registro.usado = True
        registro.save(update_fields=['usado'])
        raise   # La vista decide qué mostrar al usuario


def verificar_codigo(correo: str, codigo_ingresado: str, tipo: str) -> CodigoVerificacion | None:
    """
    Busca el código más reciente no usado para (correo, tipo) y comprueba
    que coincida y esté vigente.

    Returns:
        La instancia de CodigoVerificacion si es válido, None en caso contrario.
    """
    registro = CodigoVerificacion.objects.filter(
        correo=correo, codigo=codigo_ingresado, tipo=tipo, usado=False
    ).order_by('-creado_en').first()

    if registro and registro.esta_vigente():
        return registro
    return None


# ──────────────────────────────────────────────────────────────────────────────
# Administradores
# ──────────────────────────────────────────────────────────────────────────────

def crear_admin(codigo_id: int, username: str, password: str, correo: str) -> User:
    """
    Crea un usuario administrador (is_staff=True) y marca el código como usado.

    ACID – Atomicidad:
        La creación del usuario y el marcado del código ocurren en una sola
        transacción: si cualquiera de los dos falla, ambas operaciones se
        revierten para no dejar el sistema en un estado inconsistente.

    Raises:
        CodigoVerificacion.DoesNotExist: si el código ya fue usado o no existe.
        ValueError: si el código expiró.
        django.db.IntegrityError: si el username ya existe (raza con limpieza de form).
    """
    with transaction.atomic():
        # select_for_update evita condición de carrera si dos requests llegan
        # simultáneamente con el mismo código.
        registro = CodigoVerificacion.objects.select_for_update().get(
            id=codigo_id, tipo=CodigoVerificacion.Tipo.REGISTRO, usado=False
        )

        if not registro.esta_vigente():
            raise ValueError("El código expiró.")

        user = User.objects.create_user(
            username=username,
            email=correo,
            password=password,
            is_staff=True,
        )

        registro.usado = True
        registro.save(update_fields=['usado'])

    return user


def resetear_password(codigo_id: int, username: str, nueva_password: str) -> User:
    """
    Actualiza la contraseña de un usuario staff y marca el código como usado.

    ACID – Atomicidad:
        Igual que crear_admin: ambas escrituras van en la misma transacción.

    Raises:
        CodigoVerificacion.DoesNotExist: si el código ya fue usado o no existe.
        ValueError: si el código expiró.
        User.DoesNotExist: si el usuario no existe o no es staff.
    """
    with transaction.atomic():
        registro = CodigoVerificacion.objects.select_for_update().get(
            id=codigo_id, tipo=CodigoVerificacion.Tipo.RESET, usado=False
        )

        if not registro.esta_vigente():
            raise ValueError("El código expiró.")

        user = User.objects.get(username=username, is_staff=True)
        user.set_password(nueva_password)
        user.save()

        registro.usado = True
        registro.save(update_fields=['usado'])

    return user