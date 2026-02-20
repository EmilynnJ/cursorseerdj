from decimal import Decimal
from django.conf import settings
from django.db import models, transaction

ENTRY_TYPES = [
    ('top_up', 'Top Up'),
    ('session_charge', 'Session Charge'),
    ('booking', 'Booking'),
    ('paid_reply', 'Paid Reply'),
    ('gift', 'Gift'),
    ('refund', 'Refund'),
    ('adjustment', 'Adjustment'),
    ('payout', 'Payout'),
    ('commission', 'Commission'),
]


class Wallet(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='wallet'
    )
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    stripe_customer_id = models.CharField(max_length=255, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Wallet({self.user_id}) ${self.balance}"

    def balance_from_ledger(self):
        from django.db.models import Sum
        total = self.entries.aggregate(s=Sum('amount'))['s'] or Decimal('0')
        return total


class ProcessedStripeEvent(models.Model):
    stripe_event_id = models.CharField(max_length=255, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)


class LedgerEntry(models.Model):
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='entries')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    entry_type = models.CharField(max_length=20, choices=ENTRY_TYPES)
    idempotency_key = models.CharField(max_length=255, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    session = models.ForeignKey(
        'readings.Session',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ledger_entries'
    )
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True, db_index=True)
    stripe_event_id = models.CharField(max_length=255, blank=True, db_index=True)
    reference_type = models.CharField(max_length=50, blank=True)
    reference_id = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.entry_type} {self.amount}"


def debit_wallet(wallet, amount, entry_type, idempotency_key, session=None,
                 stripe_payment_intent_id='', stripe_event_id='',
                 reference_type='', reference_id=''):
    """Debit wallet with ledger entry. Idempotent on idempotency_key."""
    with transaction.atomic():
        if LedgerEntry.objects.filter(idempotency_key=idempotency_key).exists():
            return False
        w = Wallet.objects.select_for_update().get(pk=wallet.pk)
        if w.balance < amount:
            raise ValueError("Insufficient balance")
        LedgerEntry.objects.create(
            wallet=w,
            amount=-amount,
            entry_type=entry_type,
            idempotency_key=idempotency_key,
            session=session,
            stripe_payment_intent_id=stripe_payment_intent_id,
            stripe_event_id=stripe_event_id,
            reference_type=reference_type,
            reference_id=reference_id,
        )
        w.balance -= amount
        w.save(update_fields=['balance', 'updated_at'])
    return True


def credit_wallet(wallet, amount, entry_type, idempotency_key, session=None,
                  stripe_payment_intent_id='', stripe_event_id='',
                  reference_type='', reference_id=''):
    """Credit wallet with ledger entry. Idempotent on idempotency_key."""
    with transaction.atomic():
        if LedgerEntry.objects.filter(idempotency_key=idempotency_key).exists():
            return False
        w = Wallet.objects.select_for_update().get(pk=wallet.pk)
        LedgerEntry.objects.create(
            wallet=w,
            amount=amount,
            entry_type=entry_type,
            idempotency_key=idempotency_key,
            session=session,
            stripe_payment_intent_id=stripe_payment_intent_id,
            stripe_event_id=stripe_event_id,
            reference_type=reference_type,
            reference_id=reference_id,
        )
        w.balance += amount
        w.save(update_fields=['balance', 'updated_at'])
    return True
