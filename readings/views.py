from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.utils import timezone
from datetime import timedelta
from .models import Session, SessionNote
from readers.models import ReaderProfile, ReaderRate
from wallets.models import Wallet


@login_required
def create_session(request, reader_id):
    reader = get_object_or_404(ReaderProfile, pk=reader_id)
    
    # Check client has wallet with sufficient balance
    wallet, _ = Wallet.objects.get_or_create(user=request.user, defaults={})
    rate = ReaderRate.objects.filter(reader=reader, modality='voice').first()
    if not rate:
        rate = reader.rates.first()
    rpm = rate.rate_per_minute if rate else 0
    
    # Require at least 1 minute of balance
    if wallet.balance < rpm:
        return redirect('wallet_dashboard')
    
    session = Session.objects.create(
        client=request.user,
        reader=reader.user,
        modality=rate.modality if rate else 'voice',
        rate_per_minute=rpm,
        state='waiting',
    )
    session.channel_name = f"session_{session.pk}"
    session.save(update_fields=['channel_name'])
    session.transition('active')
    return redirect('session_detail', pk=session.pk)


@login_required
def session_view(request, pk):
    session = get_object_or_404(Session.objects.select_related('client', 'reader'), pk=pk)
    if request.user != session.client and request.user != session.reader:
        return redirect('reader_list')
    
    # Check if session should be in reconnecting state
    if session.state == 'paused' and session.grace_until and session.grace_until > timezone.now():
        session.transition('reconnecting')
    
    return render(request, 'readings/session.html', {'session': session})


@login_required
@require_POST
def session_disconnect(request, pk):
    """Handle client disconnect - enter grace period."""
    session = get_object_or_404(Session, pk=pk)
    if request.user != session.client and request.user != session.reader:
        return redirect('reader_list')
    
    if session.state == 'active':
        # Enter grace period for reconnection (5 minutes)
        session.grace_until = timezone.now() + timedelta(minutes=5)
        session.reconnect_count += 1
        session.transition('paused')
        session.save(update_fields=['grace_until', 'reconnect_count'])
    
    return redirect('session_detail', pk=pk)


@login_required
@require_POST
def session_reconnect(request, pk):
    """Handle client reconnect - resume session."""
    session = get_object_or_404(Session, pk=pk)
    if request.user != session.client and request.user != session.reader:
        return redirect('reader_list')
    
    # Check if within grace period
    if session.state == 'paused' and session.grace_until and session.grace_until > timezone.now():
        session.transition('active')
        session.grace_until = None
        session.save(update_fields=['grace_until'])
    
    return redirect('session_detail', pk=pk)


@login_required
@require_POST
def session_end(request, pk):
    """End session manually."""
    session = get_object_or_404(Session, pk=pk)
    if request.user != session.client and request.user != session.reader:
        return redirect('reader_list')

    if session.state in ('active', 'paused', 'reconnecting'):
        session.ended_at = timezone.now()
        session.transition('ended')
        session.save(update_fields=['ended_at'])

    return redirect('session_detail', pk=pk)


@login_required
@require_POST
def create_note(request, session_id):
    """Client creates a private note about a session or reader."""
    session = get_object_or_404(Session, pk=session_id, client=request.user)
    body = request.POST.get('body', '').strip()
    if body:
        SessionNote.objects.create(
            client=request.user,
            session=session,
            reader=session.reader,
            body=body,
        )
    return redirect('session_detail', pk=session_id)
