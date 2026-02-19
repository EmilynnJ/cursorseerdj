from django.contrib import admin
from .models import Wallet, LedgerEntry, ProcessedStripeEvent


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('user', 'balance', 'stripe_customer_id')


@admin.register(LedgerEntry)
class LedgerEntryAdmin(admin.ModelAdmin):
    list_display = ('wallet', 'amount', 'entry_type', 'idempotency_key', 'created_at')


@admin.register(ProcessedStripeEvent)
class ProcessedStripeEventAdmin(admin.ModelAdmin):
    list_display = ('stripe_event_id', 'created_at')
