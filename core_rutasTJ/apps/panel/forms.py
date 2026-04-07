from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password

class VerificarCodigoForm(forms.Form):
    codigo = forms.CharField(
        max_length=6,
        min_length=6,
        label="Código de verificación",
        widget=forms.TextInput(attrs={
            'placeholder': '000000',
            'class': 'form-input',
            'maxlength': '6',
        })
    )

class CrearAdminForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        label="Nombre de usuario",
        widget=forms.TextInput(attrs={
            'placeholder': 'nombre_admin',
            'class': 'form-input',
        })
    )
    password1 = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={
            'placeholder': '••••••••',
            'class': 'form-input',
        })
    )
    password2 = forms.CharField(
        label="Confirmar contraseña",
        widget=forms.PasswordInput(attrs={
            'placeholder': '••••••••',
            'class': 'form-input',
        })
    )

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Ese nombre de usuario ya está en uso.")
        return username

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('password1')
        p2 = cleaned.get('password2')
        if p1 and p2 and p1 != p2:
            self.add_error('password2', "Las contraseñas no coinciden.")
        if p1:
            # Usa los validadores de Django definidos en settings
            validate_password(p1)
        return cleaned