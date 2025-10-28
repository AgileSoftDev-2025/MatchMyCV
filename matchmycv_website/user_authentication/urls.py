from django.urls import path
from . import views

app_name = "user_authentication"

urlpatterns = [
    path('login/', views.login_view, name='login'),         # '/login/'
    path('register/', views.register_view, name='register') # '/register/'
]
