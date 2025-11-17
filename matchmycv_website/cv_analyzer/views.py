from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import FileSystemStorage
from django.conf import settings
from .cv_parser import parse_cv, get_job_recommendations, load_models
import os
import json

# Pre-load models when server starts
try:
    load_models()
    print("✅ Models pre-loaded successfully!")
except Exception as e:
    print(f"⚠️ Warning: Could not pre-load models: {e}")


def index(request):
    """Redirect root URL to the CV analysis page"""
    return redirect('analisis_cv')


def analisis_cv(request):
    """Serve the upload page"""
    return render(request, 'cv_analyzer/analisis_cv.html')


def hasil_rekomendasi(request):
    """Serve the results page"""
    return render(request, 'cv_analyzer/hasil_rekomendasi.html')


@csrf_exempt
def api_analyze_cv(request):
    """API endpoint for CV analysis"""
    if request.method == 'POST':
        try:
            cv_file = request.FILES.get('cv_file')
            location = request.POST.get('location', 'all')
            
            if not cv_file:
                return JsonResponse({'success': False, 'error': 'No file uploaded'}, status=400)
            
            # Validate file
            if cv_file.size > 10 * 1024 * 1024:
                return JsonResponse({'success': False, 'error': 'File size exceeds 10 MB limit'}, status=400)
            
            if not cv_file.name.endswith('.pdf'):
                return JsonResponse({'success': False, 'error': 'Please upload a PDF file'}, status=400)
            
            # Save file temporarily
            fs = FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT, 'temp_cv'))
            filename = fs.save(cv_file.name, cv_file)
            file_path = fs.path(filename)
            
            print(f"📄 Processing CV: {cv_file.name}")
            print(f"📍 Location filter: {location}")
            
            # Parse CV
            print("🔍 Parsing CV...")
            cv_data = parse_cv(file_path)
            print(f"✅ CV parsed: {len(cv_data.get('skills', []))} skills found")
            
            # Get job recommendations
            print("🎯 Finding job matches...")
            job_recommendations = get_job_recommendations(cv_data, location, num_results=6)
            print(f"✅ Found {len(job_recommendations)} job matches")
            
            # Clean up temp file
            if os.path.exists(file_path):
                os.remove(file_path)
            
            # Ensure all required fields exist
            response_data = {
                'success': True,
                'cv_data': {
                    'pendidikan_terakhir': cv_data.get('pendidikan_terakhir', 'Tidak Terdeteksi'),
                    'skills': cv_data.get('skills', []),
                    'pengalaman': cv_data.get('pengalaman', ['Tidak Terdeteksi'])
                },
                'job_recommendations': job_recommendations,
                'location': location
            }
            
            print("✅ Response prepared successfully")
            return JsonResponse(response_data)
        
        except Exception as e:
            print(f"❌ Error during analysis: {str(e)}")
            import traceback
            traceback.print_exc()
            return JsonResponse({
                'success': False,
                'error': f'Analysis failed: {str(e)}'
            }, status=500)
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)