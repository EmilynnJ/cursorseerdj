from django.contrib import admin
from .models import ScheduledSlot, Booking


@admin.register(ScheduledSlot)
class ScheduledSlotAdmin(admin.ModelAdmin):
    list_display = ('reader', 'start', 'end', 'duration_minutes', 'status', 'client')


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('slot', 'client', 'amount', 'cancelled_at')
