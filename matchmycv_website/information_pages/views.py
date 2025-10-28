from django.shortcuts import render

def landing_page(request):
    return render(request, 'information_pages/landing_page.html')

def about_us(request):
    return render(request, 'information_pages/tentang_kami.html')

def faq(request):
    return render(request, 'information_pages/faq.html')