from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout, get_user_model
from django.contrib import messages
from .forms import RegisterForm, EmailLoginForm
from django.utils.html import strip_tags


UserModel = get_user_model()

def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)

        # ——— PRIORITAS: jika ada field kosong → pesan "missing fields"
        posted_email = (request.POST.get('email') or '').strip()
        posted_username = (request.POST.get('username') or '').strip()
        posted_pwd1 = request.POST.get('password1') or ''
        posted_pwd2 = request.POST.get('password2') or ''

        if not posted_username or not posted_email or not posted_pwd1 or not posted_pwd2:
            messages.error(request, "Registrasi gagal. Periksa kembali data yang Anda masukkan.")
            return render(request, 'user_authentication/register.html', {'form': form})

        # Valid -> register
        if form.is_valid():
            user = form.save()
            raw_password = form.cleaned_data.get('password1')
            auth_user = authenticate(username=user.username, password=raw_password)
            if auth_user is not None:
                login(request, auth_user)
            messages.success(request, "Berhasil membuat akun!")
            return redirect('/')

        # ------- FORM TIDAK VALID: tentukan pesan sesuai feature -------
        # 1) Email sudah terdaftar → pesan spesifik feature
        if UserModel.objects.filter(email=posted_email).exists():
            messages.error(request, "Email sudah terdaftar. Silakan gunakan email lain.")
            return render(request, 'user_authentication/register.html', {'form': form})

        # 2) Analisis error code password dari form
        pesan_error = None
        try:
            data_errors = form.errors.as_data()  # dict: field -> list[ValidationError]
        except Exception:
            data_errors = {}

        pwd_codes = []
        for field in ('password1', 'password2', '__all__'):
            if field in data_errors:
                for err in data_errors[field]:
                    if getattr(err, 'code', None):
                        pwd_codes.append(err.code)

        if 'password_mismatch' in pwd_codes:
            pesan_error = "Kedua kolom password tidak sama."
        elif 'password_too_short' in pwd_codes:
            pesan_error = "Password terlalu pendek. Gunakan minimal 8 karakter."
        else:
            # Fallback standar sesuai feature
            pesan_error = "Registrasi gagal. Periksa kembali data yang Anda masukkan."

        messages.error(request, pesan_error)
        return render(request, 'user_authentication/register.html', {'form': form})

    # GET
    form = RegisterForm()
    return render(request, 'user_authentication/register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = EmailLoginForm(request.POST)

        email = (request.POST.get('email') or '').strip()
        password = request.POST.get('password') or ''
        if not email or not password:
            messages.error(request, "Login gagal. Semua field harus diisi!")
            return render(request, 'user_authentication/login.html', {'form': form})

        if not form.is_valid():
            UserModel = get_user_model()
            if not UserModel.objects.filter(email=email).exists():
                messages.error(request, "Login gagal. Email tidak terdaftar.")
            else:
                messages.error(request, "Login gagal. Email atau password Anda salah.")
            return render(request, 'user_authentication/login.html', {'form': form})

        # Field valid
        UserModel = get_user_model()
        user_obj = UserModel.objects.filter(email=email).first()
        if not user_obj:
            messages.error(request, "Login gagal. Email tidak terdaftar.")
            return render(request, 'user_authentication/login.html', {'form': form})

        user = authenticate(request, username=user_obj.username, password=password)
        if user is None:
            messages.error(request, "Login gagal. Email atau password Anda salah.")
            return render(request, 'user_authentication/login.html', {'form': form})

        login(request, user)
        messages.success(request, "Login Berhasil!")
        return redirect('/')

    form = EmailLoginForm()
    return render(request, 'user_authentication/login.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.info(request, "Berhasil Logout!")
    return redirect('/')