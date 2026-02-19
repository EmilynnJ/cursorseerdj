from celery import shared_task
from django.utils import timezone
from django.db import transaction


@shared_task
def billing_tick():
    """Every minute: charge active sessions and handle low balance."""
    from .models import Session
    from wallets.models import Wallet, LedgerEntry, debit_wallet

    now = timezone.now()
    for session in Session.objects.filter(state='active').select_related('client', 'reader'):
        try:
            wallet = Wallet.objects.get(user=session.client)
            rate = session.rate_per_minute
            if rate <= 0:
                continue
            idempotency_key = f"session_{session.pk}_min_{session.billing_minutes + 1}"
            if LedgerEntry.objects.filter(idempotency_key=idempotency_key).exists():
                continue
            if wallet.balance < rate:
                session.transition('paused')
                continue
            debit_wallet(
                wallet,
                rate,
                'session_charge',
                idempotency_key,
                session=session,
                reference_type='session',
                reference_id=str(session.pk),
            )
            session.billing_minutes += 1
            session.last_billing_at = now
            session.save(update_fields=['billing_minutes', 'last_billing_at'])
        except Wallet.DoesNotExist:
            session.transition('ended')
        except ValueError:
            session.transition('paused')
