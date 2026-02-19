from django.urls import path
from .agora_views import agora_token

urlpatterns = [
    path('sessions/<int:session_id>/agora-token/', agora_token),
]
