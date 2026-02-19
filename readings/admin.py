from django.contrib import admin
from .models import Session


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ('pk', 'client', 'reader', 'modality', 'state', 'billing_minutes', 'created_at')
