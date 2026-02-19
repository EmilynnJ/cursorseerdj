from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from .models import Livestream, Gift, GiftPurchase
from wallets.models import Wallet, debit_wallet, LedgerEntry, credit_wallet


def live_list(request):
    streams = Livestream.objects.filter(ended_at__isnull=True).select_related('reader')[:20]
    return render(request, 'live/list.html', {'streams': streams})


def stream_view(request, pk):
    stream = get_object_or_404(Livestream, pk=pk)
    gifts = Gift.objects.all()
    return render(request, 'live/stream.html', {'stream': stream, 'gifts': gifts})


@login_required
@require_POST
def send_gift(request, stream_id):
    stream = get_object_or_404(Livestream, pk=stream_id)
    gift_id = request.POST.get('gift_id')
    gift = get_object_or_404(Gift, pk=gift_id)
    wallet = Wallet.objects.get(user=request.user)
    idem = f"gift_{stream_id}_{gift_id}_{request.user.id}_{GiftPurchase.objects.filter(livestream=stream).count()}"
    try:
        debit_wallet(wallet, gift.price, 'gift', idem, reference_type='gift', reference_id=str(gift_id))
    except ValueError:
        return redirect('live_list')
    entry = LedgerEntry.objects.get(idempotency_key=idem)
    GiftPurchase.objects.create(livestream=stream, sender=request.user, gift=gift, amount=gift.price, ledger_entry=entry)
    return redirect('stream_view', pk=stream_id)
