from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'), 
    path('analisis-cv/', views.analisis_cv, name='analisis_cv'),
    path('hasil-rekomendasi/', views.hasil_rekomendasi, name='hasil_rekomendasi'),
    path('api/analyze-cv/', views.api_analyze_cv, name='api_analyze_cv'),
]