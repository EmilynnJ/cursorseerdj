from django.urls import path
from . import views
from .webhooks import stripe_webhook

urlpatterns = [
    path('', views.dashboard, name='wallet_dashboard'),
    path('topup/', views.topup_start, name='wallet_topup'),
    path('webhook/', stripe_webhook, name='stripe_webhook'),
]
