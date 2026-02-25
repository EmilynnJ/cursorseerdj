from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Sum, Count
from django.views.decorators.http import require_POST
from django.contrib.contenttypes.models import ContentType
from wallets.models import LedgerEntry, Wallet, credit_wallet, debit_wallet
from readings.models import Session
from readers.models import ReaderProfile
from community.models import Flag, ForumThread, ForumPost
from decimal import Decimal
import uuid


@staff_member_required
def admin_dashboard(request):
    total_balance = Wallet.objects.aggregate(s=Sum('balance'))['s'] or 0
    session_count = Session.objects.count()
    reader_count = ReaderProfile.objects.count()
    pending_flags = Flag.objects.filter(status='pending').count()
    return render(request, 'admin/dashboard.html', {
        'total_balance': total_balance,
        'session_count': session_count,
        'reader_count': reader_count,
        'pending_flags': pending_flags,
    })


@staff_member_required
def moderation_queue(request):
    flags = Flag.objects.filter(status='pending').select_related('reporter').order_by('-id')[:50]
    return render(request, 'admin/moderation_queue.html', {'flags': flags})


@staff_member_required
@require_POST
def resolve_flag(request, pk):
    flag = get_object_or_404(Flag, pk=pk)
    flag.status = 'resolved'
    flag.save(update_fields=['status'])
    return redirect('moderation_queue')


@staff_member_required
@require_POST
def dismiss_flag(request, pk):
    flag = get_object_or_404(Flag, pk=pk)
    flag.status = 'dismissed'
    flag.save(update_fields=['status'])
    return redirect('moderation_queue')


@staff_member_required
def refund_adjustment(request):
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        amount = request.POST.get('amount')
        entry_type = request.POST.get('type')  # refund or adjustment
        reason = request.POST.get('reason', '')[:200]
        if user_id and amount and entry_type in ('refund', 'adjustment'):
            from django.contrib.auth import get_user_model
            User = get_user_model()
            user = User.objects.filter(pk=user_id).first()
            if user:
                try:
                    amt = Decimal(str(amount))
                    if amt <= 0:
                        return redirect('refund_adjustment')
                    wallet, _ = Wallet.objects.get_or_create(user=user, defaults={})
                    idem = f"admin_{entry_type}_{uuid.uuid4()}"
                    if entry_type == 'refund':
                        credit_wallet(wallet, amt, 'refund', idem, reference_type='admin_refund', reference_id=reason)
                    else:
                        debit_wallet(wallet, amt, 'adjustment', idem, reference_type='admin_adjustment', reference_id=reason)
                except (ValueError, Exception):
                    pass
        return redirect('refund_adjustment')
    users = []
    return render(request, 'admin/refund_adjustment.html', {'users': users})


@staff_member_required
@require_POST
def trigger_payouts(request):
    """Admin manually triggers the reader payout batch task."""
    from readings.tasks import payout_readers
    payout_readers.delay()
    return redirect('admin_dashboard')
