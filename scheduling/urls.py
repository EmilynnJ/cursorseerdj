from django.urls import path
from . import views

urlpatterns = [
    path('', views.schedule_view, name='schedule'),
    path('book/<int:pk>/', views.book_slot, name='book_slot'),
    path('cancel/<int:pk>/', views.cancel_booking, name='cancel_booking'),
]
