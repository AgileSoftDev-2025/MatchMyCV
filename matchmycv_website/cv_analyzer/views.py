from django.shortcuts import render

def analisis_cv(request):
    return render(request, 'cv_analyzer/analisis_cv.html')

def hasil_rekomendasi(request):
    return render(request, 'cv_analyzer/hasil_rekomendasi.html')
