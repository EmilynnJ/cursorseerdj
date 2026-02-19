"""
Celery tasks for SoulSeer: billing, session management, webhooks.
"""

import logging
from celery import shared_task
from django.utils import timezone
from django.db import transaction
from decimal import Decimal

logger = logging.getLogger(__name__)


# ============================================================================
# BILLING TICK (Every 60 seconds)
# ============================================================================

@shared_task
def billing_tick():
    """
    Every 60 seconds: charge active sessions and handle low balance.
    
    Flow:
    1. Find all sessions in 'active' state
    2. For each: check balance, debit, increment billing_minutes
    3. On insufficient balance: pause session
    4. On error: end session
    
    Idempotency: Uses session_id + billing_minutes to prevent double-charge
    """
    from .models import Session
    from wallets.models import Wallet, LedgerEntry, debit_wallet
    
    now = timezone.now()
    active_sessions = Session.objects.filter(state='active').select_related('client', 'reader')
    
    for session in active_sessions:
        try:
            wallet = Wallet.objects.get(user=session.client)
            rate = session.rate_per_minute
            
            # Skip if no rate set
            if rate <= 0:
                logger.warning(f"Session {session.pk} has zero rate, skipping")
                continue
            
            # Idempotency check: prevent double-charging same minute
            idempotency_key = f"session_{session.pk}_min_{session.billing_minutes + 1}"
            if LedgerEntry.objects.filter(idempotency_key=idempotency_key).exists():
                logger.info(f"Session {session.pk} already charged for minute {session.billing_minutes + 1}, skipping")
                continue
            
            # Check balance
            if wallet.balance < rate:
                logger.info(f"Session {session.pk} low balance (${wallet.balance} < ${rate}), pausing")
                session.transition('paused')
                session.save()
                continue
            
            # Debit wallet (atomic transaction)
            debit_wallet(
                wallet,
                rate,
                'session_charge',
                idempotency_key,
                session=session,
                reference_type='session',
                reference_id=str(session.pk),
            )
            
            # Increment billing counter
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
            session.transition('paused')
            session.save()
        except Exception as e:
            logger.error(f"Session {session.pk} billing error: {e}")


# ============================================================================
# GRACE PERIOD EXPIRATION (Every 30 seconds)
# ============================================================================

@shared_task
def expire_grace_periods():
    """
    Check paused sessions with expired grace periods.
    Auto-end sessions after 5 min of disconnect.
    
    Flow:
    1. Find sessions in 'paused' state with grace_until < now
    2. Transition to 'ended'
    3. Queue finalization
    """
    from .models import Session
    
    now = timezone.now()
    expired = Session.objects.filter(
        state='paused',
        grace_until__isnull=False,
        grace_until__lt=now
    )
    
    for session in expired:
        logger.info(f"Session {session.pk} grace period expired, ending")
        session.transition('ended')
        session.ended_at = now
        session.save()
        session_finalize.delay(session.pk)


# ============================================================================
# SESSION FINALIZATION (Async)
# ============================================================================

@shared_task
def session_finalize(session_id):
    """
    Finalize session after it ends.
    
    Flow:
    1. Verify session state is 'ended'
    2. Reconcile ledger (ensure balance updated)
    3. Transition to 'finalized'
    4. Trigger review notification (optional)
    5. Create AuditLog entry
    
    Idempotency: Safe to call multiple times (checks finalized state)
    """
    from .models import Session
    from core.models import AuditLog
    
    try:
        session = Session.objects.get(pk=session_id)
        
        # Already finalized
        if session.state == 'finalized':
            logger.info(f"Session {session_id} already finalized, skipping")
            return
        
        # Must be in 'ended' state
        if session.state != 'ended':
            logger.warning(f"Session {session_id} not in 'ended' state, current: {session.state}")
            return
        
        # Reconcile wallet ledger (ensure all charges recorded)
        from wallets.models import Wallet
        wallet = Wallet.objects.get(user=session.client)
        ledger_sum = wallet.balance_from_ledger()
        if wallet.balance != ledger_sum:
            logger.warning(f"Session {session_id} ledger mismatch: balance={wallet.balance}, ledger_sum={ledger_sum}")
            wallet.balance = ledger_sum
            wallet.save(update_fields=['balance'])
        
        # Transition to finalized
        session.transition('finalized')
        session.save()
        
        # Audit log
        total_charge = float(session.rate_per_minute * session.billing_minutes)
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
        
        logger.info(f"Session {session_id} finalized (${total_charge}, {session.billing_minutes} min)")
        
    except Session.DoesNotExist:
        logger.error(f"Session {session_id} not found for finalization")
    except Exception as e:
        logger.error(f"Session {session_id} finalization error: {e}")


# ============================================================================
# STRIPE WEBHOOK PROCESSING
# ============================================================================

@shared_task
def process_stripe_webhook(event_dict):
    """
    Process Stripe webhook asynchronously.
    
    Events:
    - charge.succeeded: Credit wallet
    - charge.failed: Log error
    - charge.refunded: Refund wallet
    - customer.subscription.deleted: Handle subscription end
    
    Idempotency: Checked via ProcessedStripeEvent.stripe_event_id
    """
    import stripe
    from wallets.models import ProcessedStripeEvent, credit_wallet, Wallet
    
    try:
        event_id = event_dict.get('id')
        event_type = event_dict.get('type')
        
        # Check if already processed
        if ProcessedStripeEvent.objects.filter(stripe_event_id=event_id).exists():
            logger.info(f"Stripe event {event_id} already processed, skipping")
            return
        
        # Route by event type
        if event_type == 'charge.succeeded':
            data = event_dict.get('data', {}).get('object', {})
            customer_id = data.get('customer')
            amount_cents = data.get('amount')
            charge_id = data.get('id')
            
            # Find user by stripe customer
            wallet = Wallet.objects.get(stripe_customer_id=customer_id)
            amount = Decimal(str(amount_cents)) / 100
            
            # Credit wallet (idempotent)
            idempotency_key = f"stripe_{event_id}"
            credit_wallet(
                wallet,
                amount,
                'top_up',
                idempotency_key,
                stripe_payment_intent_id=charge_id,
                stripe_event_id=event_id,
                reference_type='stripe_charge',
                reference_id=charge_id,
            )
            
            logger.info(f"Wallet {wallet.id} credited ${amount} from Stripe charge {charge_id}")
        
        elif event_type == 'charge.refunded':
            data = event_dict.get('data', {}).get('object', {})
            customer_id = data.get('customer')
            amount_cents = data.get('amount_refunded', 0)
            charge_id = data.get('id')
            
            wallet = Wallet.objects.get(stripe_customer_id=customer_id)
            amount = Decimal(str(amount_cents)) / 100
            
            # Debit wallet for refund
            from wallets.models import debit_wallet
            idempotency_key = f"stripe_refund_{event_id}"
            debit_wallet(
                wallet,
                amount,
                'refund',
                idempotency_key,
                stripe_payment_intent_id=charge_id,
                stripe_event_id=event_id,
                reference_type='stripe_refund',
                reference_id=charge_id,
            )
            
            logger.info(f"Wallet {wallet.id} refunded ${amount} from Stripe charge {charge_id}")
        
        else:
            logger.info(f"Unhandled Stripe event type: {event_type}")
        
        # Mark as processed
        ProcessedStripeEvent.objects.create(stripe_event_id=event_id)
        
    except Exception as e:
        logger.error(f"Stripe webhook processing error: {e}")
        raise  # Retry on failure


# ============================================================================
# SCHEDULED TASKS (via CELERY_BEAT_SCHEDULE)
# ============================================================================

# billing_tick: Every 60 seconds (defined in settings.py)
# expire_grace_periods: Every 30 seconds (add to settings.py)

