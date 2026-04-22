from django.db import models
from django.utils import timezone
import datetime


# ──────────────────────────────────────────────────────────────────────────────
# SOLID – SRP / OCP / DRY:
#   Los dos modelos originales (CodigoRegistroAdmin y CodigoResetPassword) eran
#   idénticos en estructura.  Se unifica en uno solo con un campo `tipo` para
#   evitar duplicación y facilitar extensiones futuras sin tocar el esquema.
# ──────────────────────────────────────────────────────────────────────────────

class CodigoVerificacion(models.Model):
    """
    Código OTP de 6 dígitos enviado al correo de empresa.
    Sirve tanto para el registro de un admin como para el reset de contraseña.
    """

    class Tipo(models.TextChoices):
        REGISTRO = 'registro', 'Registro administrador'
        RESET    = 'reset',    'Reset de contraseña'

    correo    = models.EmailField()
    codigo    = models.CharField(max_length=6)
    tipo      = models.CharField(max_length=10, choices=Tipo.choices)
    creado_en = models.DateTimeField(auto_now_add=True)
    usado     = models.BooleanField(default=False)

    class Meta:
        verbose_name        = "Código de Verificación"
        verbose_name_plural = "Códigos de Verificación"
        # Índice compuesto para acelerar las búsquedas más frecuentes
        indexes = [
            models.Index(fields=['correo', 'tipo', 'usado']),
        ]

    def __str__(self):
        estado = 'usado' if self.usado else 'activo'
        return f"[{self.get_tipo_display()}] {self.correo} – {self.codigo} ({estado})"

    def esta_vigente(self) -> bool:
        """Devuelve True si el código no ha sido usado y no ha expirado (15 min)."""
        expiracion = self.creado_en + datetime.timedelta(minutes=15)
        return not self.usado and timezone.now() < expiracion


# ──────────────────────────────────────────────────────────────────────────────
# Aliases de compatibilidad (evitan romper migraciones antiguas si las hay).
# Elimínalos una vez que hayas consolidado las migraciones.
# ──────────────────────────────────────────────────────────────────────────────
CodigoRegistroAdmin  = CodigoVerificacion   # noqa: F811  (alias de migración)
CodigoResetPassword  = CodigoVerificacion   # noqa: F811  (alias de migración)