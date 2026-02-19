from django.urls import path
from . import views
from . import dashboard_views

urlpatterns = [
    path('health/', views.health_check, name='health_check'),
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('help/', views.help_center, name='help'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/client/', dashboard_views.client_dashboard, name='client_dashboard'),
    path('dashboard/reader/', dashboard_views.reader_dashboard, name='reader_dashboard'),
    path('privacy/', views.privacy, name='privacy'),
    path('terms/', views.terms, name='terms'),
]
