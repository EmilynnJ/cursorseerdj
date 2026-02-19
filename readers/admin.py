from django.contrib import admin
from .models import ReaderProfile, ReaderRate, ReaderAvailability


class ReaderRateInline(admin.TabularInline):
    model = ReaderRate
    extra = 1


class ReaderAvailabilityInline(admin.TabularInline):
    model = ReaderAvailability
    extra = 1


@admin.register(ReaderProfile)
class ReaderProfileAdmin(admin.ModelAdmin):
    list_display = ('slug', 'user', 'is_verified')
    list_filter = ('is_verified',)
    inlines = [ReaderRateInline, ReaderAvailabilityInline]
