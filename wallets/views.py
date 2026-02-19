from decimal import Decimal
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Wallet
from .stripe_services import create_checkout_session


@login_required
def dashboard(request):
    wallet, _ = Wallet.objects.get_or_create(user=request.user, defaults={})
    entries = wallet.entries.all()[:50]
    return render(request, 'wallets/dashboard.html', {
        'wallet': wallet,
        'entries': entries,
    })


@login_required
def topup_start(request):
    amount_str = request.POST.get('amount', '10')
    try:
        amount = Decimal(amount_str)
        if amount < 1 or amount > 500:
            amount = Decimal('10')
    except Exception:
        amount = Decimal('10')
    amount_cents = int(amount * 100)
    success_url = request.build_absolute_uri('/wallets/')
    cancel_url = request.build_absolute_uri('/wallets/')
    session = create_checkout_session(request.user, amount_cents, success_url, cancel_url)
    return redirect(session.url)
