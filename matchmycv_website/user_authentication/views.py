from django.shortcuts import render

def login_view(request):
    return render(request, 'user_authentication/login.html')

def register_view(request):
    return render(request, 'user_authentication/register.html')
