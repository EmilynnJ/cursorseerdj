from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from .models import ScheduledSlot, Booking
from readers.models import ReaderProfile
from wallets.models import Wallet, debit_wallet, credit_wallet


@login_required
def schedule_view(request):
    slots = ScheduledSlot.objects.filter(status='available', start__gte=timezone.now()).select_related('reader')[:50]
    return render(request, 'scheduling/schedule.html', {'slots': slots})


@login_required
def book_slot(request, pk):
    slot = get_object_or_404(ScheduledSlot, pk=pk, status='available')
    
    # Calculate amount based on reader's rate
    reader_profile = getattr(slot.reader, 'reader_profile', None)
    if reader_profile and reader_profile.rates.exists():
        rate = reader_profile.rates.first().rate_per_minute
    else:
        rate = Decimal('1.00')
    
    amount = rate * Decimal(slot.duration_minutes)
    wallet, _ = Wallet.objects.get_or_create(user=request.user, defaults={})
    idem = f"booking_{slot.pk}_{request.user.id}_{int(timezone.now().timestamp())}"
    
    try:
        debit_wallet(wallet, amount, 'booking', idem, reference_type='booking', reference_id=str(slot.pk))
    except ValueError:
        return redirect('wallet_dashboard')
    
    from wallets.models import LedgerEntry
    entry = LedgerEntry.objects.get(idempotency_key=idem)
    slot.client = request.user
    slot.status = 'booked'
    slot.save()
    Booking.objects.create(slot=slot, client=request.user, amount=amount, ledger_entry=entry)
    return redirect('schedule')


@login_required
@require_POST
def cancel_booking(request, pk):
    """Cancel a booking with refund rules."""
    slot = get_object_or_404(ScheduledSlot, pk=pk, client=request.user, status='booked')
    
    # Check cancellation window (24 hours before)
    now = timezone.now()
    time_until_slot = slot.start - now
    
    if time_until_slot < timedelta(hours=24):
        # Too late for full refund - 50% refund
        refund_percentage = Decimal('0.50')
    else:
        # Full refund if cancelled 24+ hours in advance
        refund_percentage = Decimal('1.00')
    
    # Get the booking
    booking = getattr(slot, 'booking', None)
    if not booking:
        return redirect('schedule')
    
    # Calculate refund amount
    original_amount = booking.amount
    refund_amount = original_amount * refund_percentage
    
    # Process refund to wallet
    if refund_amount > 0:
        import uuid
        refund_idem = f"refund_{booking.pk}_{int(now.timestamp())}"
        wallet, _ = Wallet.objects.get_or_create(user=request.user, defaults={})
        credit_wallet(
            wallet,
            refund_amount,
            'refund',
            refund_idem,
            reference_type='booking_cancellation',
            reference_id=str(booking.pk)
        )
    
    # Update slot and booking
    slot.status = 'cancelled'
    slot.save(update_fields=['status'])
    
    booking.cancelled_at = now
    booking.refund_amount = refund_amount
    booking.save(update_fields=['cancelled_at', 'refund_amount'])
    
    return redirect('schedule')
