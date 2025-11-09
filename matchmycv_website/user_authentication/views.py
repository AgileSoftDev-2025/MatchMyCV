from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from .forms import RegisterForm, EmailLoginForm
from django.contrib import messages

def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password1')
            user = authenticate(username=username, password=password)
            login(request, user)
            messages.success(request, "Berhasil membuat akun!")
            return redirect('/')
    else:
        form = RegisterForm()
    return render(request, 'user_authentication/register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = EmailLoginForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data['user']
            login(request, user)
            messages.success(request, "Login Berhasil!")
            return redirect('/')
        
    else:
        form = EmailLoginForm()
        messages.error(request, "Login gagal. Periksa kembali email/password!")
    return render(request, 'user_authentication/login.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.info(request, "Berhasil Logout!")
    return redirect('/')