from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from accounts.decorators import require_role


@login_required
def client_dashboard(request):
    from wallets.models import Wallet
    from scheduling.models import Booking
    from readers.models import Favorite
    from readings.models import SessionNote

    wallet, _ = Wallet.objects.get_or_create(user=request.user, defaults={})
    entries = wallet.entries.all()[:10]
    bookings = Booking.objects.filter(client=request.user).select_related('slot__reader').order_by('-slot__start')[:10]
    favorites = Favorite.objects.filter(client=request.user).select_related('reader__user').all()
    notes = SessionNote.objects.filter(client=request.user).order_by('-created_at')[:10]
    return render(request, 'core/client_dashboard.html', {
        'wallet': wallet,
        'entries': entries,
        'bookings': bookings,
        'favorites': favorites,
        'notes': notes,
    })


@login_required
@require_role('reader')
def reader_dashboard(request):
    from readers.models import ReaderProfile
    from readings.models import Session
    from decimal import Decimal

    rp = getattr(request.user, 'reader_profile', None)
    if not rp:
        return redirect('profile')
    sessions = Session.objects.filter(reader=request.user).select_related('client').order_by('-created_at')[:20]
    earnings = sum((s.rate_per_minute * s.billing_minutes for s in sessions), Decimal('0'))
    return render(request, 'core/reader_dashboard.html', {
        'reader_profile': rp,
        'sessions': sessions,
        'earnings': earnings,
    })
