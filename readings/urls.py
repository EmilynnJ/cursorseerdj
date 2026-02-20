from django.urls import path
from . import views

urlpatterns = [
    path('create/<int:reader_id>/', views.create_session, name='session_create'),
    path('<int:pk>/', views.session_view, name='session_detail'),
    path('<int:pk>/disconnect/', views.session_disconnect, name='session_disconnect'),
    path('<int:pk>/reconnect/', views.session_reconnect, name='session_reconnect'),
    path('<int:pk>/end/', views.session_end, name='session_end'),
    path('<int:session_id>/note/', views.create_note, name='session_create_note'),
]
