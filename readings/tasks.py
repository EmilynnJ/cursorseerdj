"""
Celery tasks for SoulSeer: billing, session management, webhooks.
"""

import logging
from celery import shared_task
from django.utils import timezone
from django.db import transaction
from decimal import Decimal

logger = logging.getLogger(__name__)


@shared_task
def billing_tick():
    """
    Every 60 seconds: charge active sessions and handle low balance.
    Idempotency: Uses session_id + billing_minutes to prevent double-charge.
    """
    from .models import Session
    from wallets.models import Wallet, LedgerEntry, debit_wallet

    now = timezone.now()
    active_sessions = Session.objects.filter(state='active').select_related('client', 'reader')

    for session in active_sessions:
        try:
            wallet = Wallet.objects.get(user=session.client)
            rate = session.rate_per_minute

            if rate <= 0:
                logger.warning(f"Session {session.pk} has zero rate, skipping")
                continue

            idempotency_key = f"session_{session.pk}_min_{session.billing_minutes + 1}"
            if LedgerEntry.objects.filter(idempotency_key=idempotency_key).exists():
                logger.info(f"Session {session.pk} already charged for minute {session.billing_minutes + 1}, skipping")
                continue

            if wallet.balance < rate:
                logger.info(f"Session {session.pk} low balance (${wallet.balance} < ${rate}), pausing")
                session.grace_until = now + timezone.timedelta(minutes=2)
                session.reconnect_count += 1
                session.transition('paused')
                session.save(update_fields=['grace_until', 'reconnect_count'])
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

            logger.info(f"Session {session.pk} charged for minute {session.billing_minutes}")

        except Wallet.DoesNotExist:
            logger.error(f"Session {session.pk} wallet not found, ending session")
            session.transition('ended')
            session.ended_at = now
            session.save()
        except ValueError as e:
            logger.warning(f"Session {session.pk} insufficient balance error: {e}, pausing")
            session.grace_until = now + timezone.timedelta(minutes=2)
            session.transition('paused')
            session.save(update_fields=['grace_until'])
        except Exception as e:
            logger.error(f"Session {session.pk} billing error: {e}")


@shared_task
def expire_grace_periods():
    """
    Check paused/reconnecting sessions with expired grace periods.
    Auto-end sessions after grace window expires.
    """
    from .models import Session

    now = timezone.now()
    expired = Session.objects.filter(
        state__in=['paused', 'reconnecting'],
        grace_until__isnull=False,
        grace_until__lt=now
    )

    for session in expired:
        logger.info(f"Session {session.pk} grace period expired, ending")
        session.transition('ended')
        session.ended_at = now
        session.save(update_fields=['ended_at'])
        session_finalize.delay(session.pk)


@shared_task
def handle_reconnect_timeout():
    """End sessions stuck in reconnecting state past grace period."""
    from .models import Session

    now = timezone.now()
    timed_out = Session.objects.filter(
        state='reconnecting',
        grace_until__lte=now
    )

    for session in timed_out:
        session.summary = (
            f"Session ended due to reconnect timeout. "
            f"Billed minutes: {session.billing_minutes}. "
            f"Reconnection attempts: {session.reconnect_count}."
        )
        session.transition('ended')
        session.ended_at = now
        session.save(update_fields=['summary', 'ended_at'])
        session_finalize.delay(session.pk)


@shared_task
def finalize_sessions():
    """Finalize ended sessions - run every 5 minutes."""
    from .models import Session

    cutoff = timezone.now() - timezone.timedelta(minutes=5)
    sessions_to_finalize = Session.objects.filter(
        state='ended',
        ended_at__lte=cutoff
    )

    for session in sessions_to_finalize:
        session_finalize.delay(session.pk)


@shared_task
def session_finalize(session_id):
    """
    Finalize a single session after it ends.
    Reconciles ledger and transitions to 'finalized'.
    Idempotent: safe to call multiple times.
    """
    from .models import Session
    from core.models import AuditLog

    try:
        session = Session.objects.get(pk=session_id)

        if session.state == 'finalized':
            logger.info(f"Session {session_id} already finalized, skipping")
            return

        if session.state != 'ended':
            logger.warning(f"Session {session_id} not in 'ended' state, current: {session.state}")
            return

        # Reconcile wallet ledger
        from wallets.models import Wallet
        try:
            wallet = Wallet.objects.get(user=session.client)
            ledger_sum = wallet.balance_from_ledger()
            if wallet.balance != ledger_sum:
                logger.warning(f"Session {session_id} ledger mismatch: balance={wallet.balance}, ledger_sum={ledger_sum}")
                wallet.balance = ledger_sum
                wallet.save(update_fields=['balance'])
        except Wallet.DoesNotExist:
            pass

        total_charge = float(session.rate_per_minute * session.billing_minutes)
        session.summary = (
            f"Session completed. Duration: {session.billing_minutes} minutes. "
            f"Total charged: ${total_charge:.2f}. Modality: {session.modality}."
        )
        session.transition('finalized')
        session.save(update_fields=['summary'])

        AuditLog.objects.create(
            user=session.client,
            action='session_finalized',
            model_name='Session',
            object_id=str(session.id),
            details={
                'modality': session.modality,
                'billing_minutes': session.billing_minutes,
                'rate_per_minute': str(session.rate_per_minute),
                'total_charge': total_charge,
            }
        )

        logger.info(f"Session {session_id} finalized (${total_charge:.2f}, {session.billing_minutes} min)")

    except Session.DoesNotExist:
        logger.error(f"Session {session_id} not found for finalization")
    except Exception as e:
        logger.error(f"Session {session_id} finalization error: {e}")


@shared_task
def process_stripe_webhook(event_dict):
    """
    Process Stripe webhook asynchronously. Idempotent via ProcessedStripeEvent.
    """
    from wallets.models import ProcessedStripeEvent, credit_wallet, debit_wallet, Wallet

    try:
        event_id = event_dict.get('id')
        event_type = event_dict.get('type')

        if ProcessedStripeEvent.objects.filter(stripe_event_id=event_id).exists():
            logger.info(f"Stripe event {event_id} already processed, skipping")
            return

        if event_type == 'charge.succeeded':
            data = event_dict.get('data', {}).get('object', {})
            customer_id = data.get('customer')
            amount_cents = data.get('amount')
            charge_id = data.get('id')

            wallet = Wallet.objects.get(stripe_customer_id=customer_id)
            amount = Decimal(str(amount_cents)) / 100
            idempotency_key = f"stripe_{event_id}"
            credit_wallet(
                wallet, amount, 'top_up', idempotency_key,
                stripe_payment_intent_id=charge_id,
                stripe_event_id=event_id,
            )
            logger.info(f"Wallet {wallet.id} credited ${amount}")

        elif event_type == 'charge.refunded':
            data = event_dict.get('data', {}).get('object', {})
            customer_id = data.get('customer')
            amount_cents = data.get('amount_refunded', 0)
            charge_id = data.get('id')

            wallet = Wallet.objects.get(stripe_customer_id=customer_id)
            amount = Decimal(str(amount_cents)) / 100
            idempotency_key = f"stripe_refund_{event_id}"
            debit_wallet(
                wallet, amount, 'refund', idempotency_key,
                reference_type='stripe_refund',
                reference_id=charge_id,
            )
            logger.info(f"Wallet {wallet.id} refunded ${amount}")

        else:
            logger.info(f"Unhandled Stripe event type: {event_type}")

        ProcessedStripeEvent.objects.create(stripe_event_id=event_id)

    except Exception as e:
        logger.error(f"Stripe webhook processing error: {e}")
        raise
