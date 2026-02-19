from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from accounts.decorators import require_role
from django.db.models import Sum, Count, Avg
from decimal import Decimal
from django.utils import timezone


@login_required
def client_dashboard(request):
    """Client dashboard: wallet, sessions, bookings, favorites, notes."""
    from wallets.models import Wallet, LedgerEntry
    from scheduling.models import Booking
    from readers.models import Favorite
    from readings.models import SessionNote, Session

    wallet, _ = Wallet.objects.get_or_create(user=request.user, defaults={})
    
    # Recent transactions
    recent_entries = wallet.entries.select_related('session').order_by('-created_at')[:10]
    
    # Scheduled bookings (upcoming)
    upcoming_bookings = Booking.objects.filter(
        client=request.user, 
        cancelled_at__isnull=True,
        slot__start__gte=timezone.now()
    ).select_related('slot__reader__user').order_by('slot__start')[:5]
    
    # Past sessions
    past_sessions = Session.objects.filter(
        client=request.user,
        state='finalized'
    ).select_related('reader').order_by('-ended_at')[:5]
    
    # Favorites
    favorites = Favorite.objects.filter(client=request.user).select_related('reader__user')
    
    # Notes
    notes = SessionNote.objects.filter(client=request.user).order_by('-created_at')[:10]
    
    # Stats
    total_spent = wallet.entries.filter(
        amount__lt=0,
        entry_type__in=['session_charge', 'paid_reply', 'gift', 'booking']
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    total_spent = abs(total_spent)
    
    return render(request, 'core/client_dashboard.html', {
        'wallet': wallet,
        'recent_entries': recent_entries,
        'upcoming_bookings': upcoming_bookings,
        'past_sessions': past_sessions,
        'favorites': favorites,
        'notes': notes,
        'total_spent': total_spent,
    })


@login_required
@require_role('reader')
def reader_dashboard(request):
    """Reader dashboard: earnings, sessions, rates, availability, analytics."""
    from readers.models import ReaderProfile, ReaderRate, ReaderAvailability, Review
    from readings.models import Session
    from scheduling.models import Booking
    from live.models import GiftPurchase
    from wallets.models import LedgerEntry

    rp = getattr(request.user, 'reader_profile', None)
    if not rp:
        return redirect('profile')
    
    # Sessions and earnings
    sessions = Session.objects.filter(reader=request.user).select_related('client').order_by('-created_at')[:20]
    session_earnings = LedgerEntry.objects.filter(
        wallet__user=request.user,
        entry_type='session_charge'
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    session_earnings = abs(session_earnings)
    
    # Gift earnings (70% split)
    gift_entries = LedgerEntry.objects.filter(
        wallet__user=request.user,
        entry_type='commission'
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    gift_earnings = abs(gift_entries)
    
    # Scheduled bookings (upcoming)
    upcoming_bookings = Booking.objects.filter(
        slot__reader=rp,
        cancelled_at__isnull=True,
        slot__start__gte=timezone.now()
    ).select_related('slot__client').order_by('slot__start')[:5]
    
    # Rates
    rates = rp.rates.all()
    
    # Availability
    availability = rp.availability.all().order_by('day_of_week')
    
    # Reviews and rating
    reviews = rp.reviews.all().order_by('-created_at')[:10]
    avg_rating = rp.reviews.aggregate(avg=Avg('rating'))['avg'] or 0
    
    total_earnings = session_earnings + gift_earnings
    
    return render(request, 'core/reader_dashboard.html', {
        'reader_profile': rp,
        'sessions': sessions,
        'session_earnings': session_earnings,
        'gift_earnings': gift_earnings,
        'total_earnings': total_earnings,
        'upcoming_bookings': upcoming_bookings,
        'rates': rates,
        'availability': availability,
        'reviews': reviews,
        'avg_rating': avg_rating,
        'review_count': reviews.count(),
    })


@login_required
@require_role('admin')
def admin_dashboard(request):
    """Admin dashboard: reader onboarding, moderation, refunds, payouts, analytics."""
    from readers.models import ReaderProfile
    from community.models import Flag
    from wallets.models import LedgerEntry, Wallet
    from readings.models import Session
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    
    # Reader onboarding
    pending_readers = ReaderProfile.objects.filter(is_verified=False).order_by('-created_at')[:10]
    verified_readers = ReaderProfile.objects.filter(is_verified=True).count()
    
    # Moderation queue
    pending_flags = Flag.objects.filter(status='pending').order_by('-id')[:10]
    resolved_flags = Flag.objects.filter(status='resolved').count()
    
    # Recent refunds
    recent_refunds = LedgerEntry.objects.filter(
        entry_type='refund'
    ).select_related('wallet__user').order_by('-created_at')[:10]
    
    # Platform stats
    total_users = User.objects.count()
    active_readers = ReaderProfile.objects.filter(is_verified=True).count()
    total_sessions = Session.objects.filter(state='finalized').count()
    total_revenue = LedgerEntry.objects.filter(
        entry_type__in=['session_charge', 'booking', 'commission']
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    total_revenue = abs(total_revenue)
    
    return render(request, 'core/admin_dashboard.html', {
        'pending_readers': pending_readers,
        'verified_readers': verified_readers,
        'pending_flags': pending_flags,
        'resolved_flags': resolved_flags,
        'recent_refunds': recent_refunds,
        'total_users': total_users,
        'active_readers': active_readers,
        'total_sessions': total_sessions,
        'total_revenue': total_revenue,
    })
