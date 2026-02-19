from celery import shared_task
from django.utils import timezone
from django.db import transaction
from decimal import Decimal


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


@shared_task
def finalize_sessions():
    """Finalize ended sessions and record summary."""
    from .models import Session
    
    # Finalize sessions that have been ended for more than 5 minutes
    cutoff = timezone.now() - timezone.timedelta(minutes=5)
    
    sessions_to_finalize = Session.objects.filter(
        state='ended',
        ended_at__lte=cutoff
    ).select_related('client', 'reader')
    
    for session in sessions_to_finalize:
        # Calculate total charged
        total_charged = session.billing_minutes * session.rate_per_minute
        
        # Create summary
        session.summary = (
            f"Session completed. Duration: {session.billing_minutes} minutes. "
            f"Total charged: ${total_charged}. Modality: {session.modality}."
        )
        session.transition('finalized')
        session.save(update_fields=['summary'])


@shared_task
def handle_reconnect_timeout():
    """End sessions stuck in reconnecting state past grace period."""
    from .models import Session
    
    now = timezone.now()
    
    # Find sessions in reconnecting state past grace period
    timed_out_sessions = Session.objects.filter(
        state='reconnecting',
        grace_until__lte=now
    )
    
    for session in timed_out_sessions:
        # Record that session ended due to reconnect timeout
        session.summary = (
            f"Session ended due to reconnect timeout. "
            f"Billed minutes: {session.billing_minutes}. "
            f"Reconnection attempts: {session.reconnect_count}."
        )
        session.transition('ended')
        session.save(update_fields=['summary', 'ended_at'])
