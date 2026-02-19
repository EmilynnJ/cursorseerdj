from django.conf import settings


def settings_ctx(request):
    """Expose selected settings to templates."""
    return {
        'STRIPE_PUBLISHABLE_KEY': getattr(settings, 'STRIPE_PUBLISHABLE_KEY', ''),
        'AGORA_APP_ID': getattr(settings, 'AGORA_APP_ID', ''),
    }
