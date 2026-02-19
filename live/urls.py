from django.urls import path
from . import views

urlpatterns = [
    path('', views.live_list, name='live_list'),
    path('<int:pk>/', views.stream_view, name='stream_view'),
    path('<int:stream_id>/gift/', views.send_gift, name='send_gift'),
]
