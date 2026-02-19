from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import ScheduledSlot, Booking
from readers.models import ReaderProfile
from wallets.models import Wallet, debit_wallet


@login_required
def schedule_view(request):
    slots = ScheduledSlot.objects.filter(status='available', start__gte=timezone.now()).select_related('reader')[:50]
    return render(request, 'scheduling/schedule.html', {'slots': slots})


@login_required
def book_slot(request, pk):
    slot = get_object_or_404(ScheduledSlot, pk=pk, status='available')
    amount = (slot.duration_minutes / 60) * 50
    from decimal import Decimal
    amount = Decimal(str(amount))
    wallet = Wallet.objects.get(user=request.user)
    idem = f"booking_{slot.pk}_{request.user.id}"
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
