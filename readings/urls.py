from django.urls import path
from . import views

urlpatterns = [
    path('create/<int:reader_id>/', views.create_session, name='session_create'),
    path('<int:pk>/', views.session_view, name='session_detail'),
]
