from decimal import Decimal
from django.conf import settings
from django.db import models

SLOT_STATUS = [
    ('available', 'Available'),
    ('booked', 'Booked'),
    ('completed', 'Completed'),
    ('cancelled', 'Cancelled'),
]


class ScheduledSlot(models.Model):
    reader = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='scheduled_slots',
    )
    start = models.DateTimeField()
    end = models.DateTimeField()
    duration_minutes = models.PositiveSmallIntegerField(default=30)
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='booked_slots',
    )
    status = models.CharField(max_length=20, choices=SLOT_STATUS, default='available', db_index=True)

    class Meta:
        ordering = ['start']


class Booking(models.Model):
    slot = models.OneToOneField(ScheduledSlot, on_delete=models.CASCADE, related_name='booking')
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='bookings',
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0'))
    ledger_entry = models.ForeignKey(
        'wallets.LedgerEntry',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='booking',
    )
    cancelled_at = models.DateTimeField(null=True, blank=True)
    refund_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
