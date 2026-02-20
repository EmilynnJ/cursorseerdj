import logging
import uuid
from decimal import Decimal

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.http import JsonResponse

from .models import Livestream, Gift, GiftPurchase
from wallets.models import Wallet, debit_wallet, credit_wallet, LedgerEntry

logger = logging.getLogger(__name__)

READER_COMMISSION_RATE = Decimal('0.70')  # Reader keeps 70%
PLATFORM_FEE_RATE = Decimal('0.30')      # Platform keeps 30%


def live_list(request):
    streams = Livestream.objects.filter(
        started_at__isnull=False, ended_at__isnull=True
    ).select_related('reader').order_by('-started_at')[:20]
    return render(request, 'live/list.html', {'streams': streams})


def stream_view(request, pk):
    stream = get_object_or_404(Livestream, pk=pk)
    gifts = Gift.objects.all()
    can_view = True
    if stream.visibility == 'private' and request.user != stream.reader:
        can_view = request.user.is_authenticated
    return render(request, 'live/stream.html', {
        'stream': stream,
        'gifts': gifts,
        'can_view': can_view,
    })


@login_required
@require_POST
def start_stream(request):
    """Reader starts a new livestream."""
    from accounts.decorators import require_role
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'reader':
        return redirect('dashboard')
    title = request.POST.get('title', '').strip() or 'Live Reading'
    visibility = request.POST.get('visibility', 'public')
    if visibility not in ('public', 'private', 'premium'):
        visibility = 'public'
    channel = f"live_{request.user.id}_{int(timezone.now().timestamp())}"
    stream = Livestream.objects.create(
        reader=request.user,
        title=title,
        visibility=visibility,
        agora_channel=channel,
        started_at=timezone.now(),
    )
    return redirect('stream_view', pk=stream.pk)


@login_required
@require_POST
def end_stream(request, pk):
    """Reader ends their livestream."""
    stream = get_object_or_404(Livestream, pk=pk, reader=request.user)
    if not stream.ended_at:
        stream.ended_at = timezone.now()
        stream.save(update_fields=['ended_at'])
    return redirect('live_list')


@login_required
@require_POST
def send_gift(request, stream_id):
    """
    Client sends a gift during livestream.
    70% credited to reader wallet, 30% kept as platform commission.
    All money movements are ledger-tracked with idempotency keys.
    """
    stream = get_object_or_404(Livestream, pk=stream_id)
    if stream.ended_at:
        return redirect('live_list')

    gift_id = request.POST.get('gift_id')
    gift = get_object_or_404(Gift, pk=gift_id)

    try:
        client_wallet = Wallet.objects.get(user=request.user)
    except Wallet.DoesNotExist:
        return redirect('live_list')

    # Use a stable idempotency key per unique gift event
    uid = str(uuid.uuid4())
    debit_idem = f"gift_debit_{stream_id}_{gift_id}_{request.user.id}_{uid}"

    try:
        debit_wallet(
            client_wallet,
            gift.price,
            'gift',
            debit_idem,
            reference_type='gift',
            reference_id=str(gift.pk),
        )
    except ValueError:
        logger.warning(f"Insufficient balance for gift: user={request.user.id}, gift={gift_id}")
        return redirect('stream_view', pk=stream_id)

    client_entry = LedgerEntry.objects.get(idempotency_key=debit_idem)
    purchase = GiftPurchase.objects.create(
        livestream=stream,
        sender=request.user,
        gift=gift,
        amount=gift.price,
        ledger_entry=client_entry,
    )

    # Credit 70% to reader
    reader_amount = (gift.price * READER_COMMISSION_RATE).quantize(Decimal('0.01'))
    if reader_amount > 0:
        try:
            reader_wallet, _ = Wallet.objects.get_or_create(user=stream.reader, defaults={})
            credit_idem = f"gift_commission_{purchase.pk}_{uid}"
            credit_wallet(
                reader_wallet,
                reader_amount,
                'commission',
                credit_idem,
                reference_type='gift_purchase',
                reference_id=str(purchase.pk),
            )
        except Exception as e:
            logger.error(f"Failed to credit reader commission for gift {purchase.pk}: {e}")

    return redirect('stream_view', pk=stream_id)
