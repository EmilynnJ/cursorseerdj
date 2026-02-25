from django.urls import path
from . import views

urlpatterns = [
    path('', views.live_list, name='live_list'),
    path('start/', views.start_stream, name='start_stream'),
    path('<int:pk>/', views.stream_view, name='stream_view'),
    path('<int:pk>/end/', views.end_stream, name='end_stream'),
    path('<int:stream_id>/gift/', views.send_gift, name='send_gift'),
]
