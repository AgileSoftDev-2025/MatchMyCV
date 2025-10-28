from django.urls import path
from . import views

app_name = "cv_analyzer"

urlpatterns = [
    path('', views.analisis_cv, name='analisis_cv'),                        # '/analisis-cv/'
    path('hasil-rekomendasi/', views.hasil_rekomendasi, name='hasil_rekomendasi'),      # '/analisis-cv/hasil-rekomendasi/'
]