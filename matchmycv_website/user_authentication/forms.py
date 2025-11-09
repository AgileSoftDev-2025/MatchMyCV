from django import forms
from django.contrib.auth import authenticate
from django.core.exceptions import MultipleObjectsReturned
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

class RegisterForm(UserCreationForm):
    email = forms.EmailField()

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']


class EmailLoginForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)

    def clean(self):
        cleaned = super().clean()
        email = cleaned.get('email')
        password = cleaned.get('password')

        if not email or not password:
            return cleaned

        try:
            user_obj = User.objects.get(email=email)
        except User.DoesNotExist:
            raise forms.ValidationError("Email tidak terdaftar.")
        except MultipleObjectsReturned:
            raise forms.ValidationError("Email terdaftar pada lebih dari satu akun. Gunakan username.")

        user = authenticate(username=user_obj.username, password=password)
        if user is None:
            raise forms.ValidationError("Email atau password salah.")
        if not user.is_active:
            raise forms.ValidationError("Akun dinonaktifkan.")

        cleaned['user'] = user
        return cleaned