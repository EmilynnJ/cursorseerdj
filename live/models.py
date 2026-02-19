from decimal import Decimal
from django.conf import settings
from django.db import models

VISIBILITY_CHOICES = [
    ('public', 'Public'),
    ('private', 'Private'),
    ('premium', 'Premium'),
]


class Livestream(models.Model):
    reader = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='livestreams',
    )
    title = models.CharField(max_length=255)
    visibility = models.CharField(max_length=20, choices=VISIBILITY_CHOICES, default='public')
    agora_channel = models.CharField(max_length=255, blank=True, db_index=True)
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)


class Gift(models.Model):
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0'))
    animation_id = models.CharField(max_length=100, blank=True)


class GiftPurchase(models.Model):
    livestream = models.ForeignKey(Livestream, on_delete=models.CASCADE, related_name='gifts')
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='gift_purchases',
    )
    gift = models.ForeignKey(Gift, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0'))
    ledger_entry = models.ForeignKey(
        'wallets.LedgerEntry',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
