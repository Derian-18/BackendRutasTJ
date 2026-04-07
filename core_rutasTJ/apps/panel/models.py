from django.db import models
from django.utils import timezone
import datetime

class CodigoRegistroAdmin(models.Model):
    """
    Almacena el código de verificación enviado al correo de empresa
    para poder crear una cuenta administrador.
    """
    correo      = models.EmailField()
    codigo      = models.CharField(max_length=6)
    creado_en   = models.DateTimeField(auto_now_add=True)
    usado       = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Código de Registro Admin"
        verbose_name_plural = "Códigos de Registro Admin"

    def __str__(self):
        return f"{self.correo} - {self.codigo} ({'usado' if self.usado else 'activo'})"

    def esta_vigente(self):
        """El código expira 15 minutos después de crearse."""
        expiracion = self.creado_en + datetime.timedelta(minutes=15)
        return not self.usado and timezone.now() < expiracion