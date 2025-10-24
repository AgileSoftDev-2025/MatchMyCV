from django.urls import path
from . import views

app_name = "information_pages"

urlpatterns = [
    path('',  views.landing_page, name='landing_page'),                
    path('tentang-kami/', views.about_us, name='about'), 
    path('faq/', views.faq, name='faq'),          
]