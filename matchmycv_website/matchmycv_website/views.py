from django.http import HttpResponse
# panggil render
from django.shortcuts import render

def index(request):
    return render(request, 'index.html')

def index1(request):
    return HttpResponse("ini beranda")

def aboutUs(request):
    return HttpResponse("ini aboutUs")

def faq(request):
    return HttpResponse("ini faq")

def analisisCV(request):
    return HttpResponse("analisis")

def hasilRekomendasi(request):
    return HttpResponse("hasil rekomendasi")

def login(request):
    return HttpResponse("login")

def register(request):
    return HttpResponse("register")