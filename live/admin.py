from django.contrib import admin
from .models import Livestream, Gift, GiftPurchase


@admin.register(Livestream)
class LivestreamAdmin(admin.ModelAdmin):
    list_display = ('title', 'reader', 'visibility', 'started_at')


@admin.register(Gift)
class GiftAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'animation_id')


@admin.register(GiftPurchase)
class GiftPurchaseAdmin(admin.ModelAdmin):
    list_display = ('livestream', 'sender', 'gift', 'amount')
