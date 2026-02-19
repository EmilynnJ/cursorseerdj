"""
SoulSeer URL configuration.
"""
from django.contrib import admin
from django.urls import path, include
from core.admin_views import (
    admin_dashboard,
    moderation_queue,
    resolve_flag,
    dismiss_flag,
    refund_adjustment,
)

urlpatterns = [
    path('admin/dashboard/', admin_dashboard, name='admin_dashboard'),
    path('admin/moderation/', moderation_queue, name='moderation_queue'),
    path('admin/moderation/<int:pk>/resolve/', resolve_flag, name='resolve_flag'),
    path('admin/moderation/<int:pk>/dismiss/', dismiss_flag, name='dismiss_flag'),
    path('admin/refunds/', refund_adjustment, name='refund_adjustment'),
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('accounts/', include('accounts.urls')),
    path('wallets/', include('wallets.urls')),
    path('stripe/webhook/', include('wallets.webhook_urls')),
    path('readers/', include('readers.urls')),
    path('sessions/', include('readings.urls')),
    path('messages/', include('messaging.urls')),
    path('scheduling/', include('scheduling.urls')),
    path('live/', include('live.urls')),
    path('shop/', include('shop.urls')),
    path('community/', include('community.urls')),
    path('api/', include('readings.api_urls')),
]
