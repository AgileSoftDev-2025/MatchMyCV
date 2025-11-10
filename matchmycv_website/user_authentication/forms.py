from django import forms
from django.contrib.auth import authenticate, get_user_model
from django.core.exceptions import MultipleObjectsReturned, ValidationError
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

UserModel = get_user_model()

class RegisterForm(UserCreationForm):
    email = forms.EmailField()

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def clean_email(self):
        email = (self.cleaned_data.get('email') or '').strip()
        if UserModel.objects.filter(email=email).exists():
            # kode error supaya bisa dipetakan jika ingin (opsional)
            raise ValidationError(
                "Email sudah terdaftar. Silakan gunakan email lain.",
                code="email_exists"
            )
        return email
    
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
        except (User.DoesNotExist, MultipleObjectsReturned):
            return cleaned

        user = authenticate(username=user_obj.username, password=password)
        if user:
            cleaned['user'] = user
        return cleaned
