# Core view utilities for dashboard, authentication, and role-based access

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum, Count, Avg
from django.utils import timezone
from datetime import timedelta

from accounts.models import UserProfile
from readings.models import Session
from wallets.models import Wallet, LedgerEntry
from readers.models import ReaderProfile, Review, ReaderRate
from scheduling.models import ScheduledSlot, Booking
from live.models import Livestream, GiftPurchase


@login_required
def client_dashboard(request):
    """Client dashboard with wallet, sessions, bookings, notes."""
    wallet = Wallet.objects.get(user=request.user)
    
    # Recent transactions
    transactions = LedgerEntry.objects.filter(wallet=wallet).select_related('session').order_by('-created_at')[:10]
    
    # Upcoming bookings
    upcoming_bookings = Booking.objects.filter(
        slot__client=request.user,
        slot__status='booked',
        slot__start__gte=timezone.now()
    ).select_related('slot__reader').order_by('slot__start')[:5]
    
    # Recent sessions
    recent_sessions = Session.objects.filter(
        client=request.user,
        state__in=['ended', 'finalized']
    ).select_related('reader').order_by('-ended_at')[:10]
    
    # Favorites
    favorites = request.user.profile.favorites.all().select_related('reader_profile')
    
    # Session notes
    notes = request.user.directmessage_set.all().order_by('-created_at')[:5]
    
    context = {
        'wallet': wallet,
        'balance': wallet.balance,
        'transactions': transactions,
        'upcoming_bookings': upcoming_bookings,
        'recent_sessions': recent_sessions,
        'favorites': favorites,
        'notes': notes,
    }
    return render(request, 'core/client_dashboard.html', context)


@login_required
def reader_dashboard(request):
    """Reader dashboard with earnings, sessions, rates, availability."""
    reader_profile = ReaderProfile.objects.get(user=request.user)
    
    # Earnings this month
    start_month = timezone.now().replace(day=1)
    session_charges = LedgerEntry.objects.filter(
        wallet__user=request.user,
        entry_type='commission',
        created_at__gte=start_month
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    gift_commissions = LedgerEntry.objects.filter(
        wallet__user=request.user,
        entry_type='commission',
        created_at__gte=start_month
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    total_earnings = session_charges + gift_commissions
    
    # Recent sessions
    recent_sessions = Session.objects.filter(
        reader=reader_profile,
        state__in=['ended', 'finalized']
    ).select_related('client').order_by('-ended_at')[:10]
    
    # Rates
    rates = ReaderRate.objects.filter(reader=reader_profile)
    rates_dict = {r.modality: r.rate_per_minute for r in rates}
    
    # Availability
    availability = request.user.profile.reader_profile.availability_set.all()
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    availability_by_day = []
    for day_num in range(7):
        day_avail = availability.filter(day_of_week=day_num).first()
        if day_avail:
            status = f"{day_avail.start_time.strftime('%H:%M')} - {day_avail.end_time.strftime('%H:%M')}"
        else:
            status = None
        availability_by_day.append((days[day_num], status))
    
    # Reviews
    reviews = Review.objects.filter(reader=reader_profile).order_by('-created_at')
    avg_rating = reviews.aggregate(avg=Avg('rating'))['avg'] or 0
    
    # Upcoming sessions
    upcoming_sessions = Booking.objects.filter(
        slot__reader=reader_profile,
        slot__status='booked',
        slot__start__gte=timezone.now()
    ).select_related('slot__client').order_by('slot__start')[:5]
    
    context = {
        'reader_profile': reader_profile,
        'session_income': session_charges,
        'commission_income': gift_commissions,
        'total_earnings': total_earnings,
        'payout_available': total_earnings,  # Simplified; real logic would check restrictions
        'recent_sessions': recent_sessions,
        'text_rate': rates_dict.get('text'),
        'voice_rate': rates_dict.get('voice'),
        'video_rate': rates_dict.get('video'),
        'availability_by_day': availability_by_day,
        'latest_reviews': reviews[:5],
        'avg_rating': avg_rating,
        'total_reviews': reviews.count(),
        'upcoming_sessions': upcoming_sessions,
    }
    return render(request, 'core/reader_dashboard.html', context)


@login_required
def admin_dashboard(request):
    """Admin dashboard with platform stats, moderation, pending readers."""
    if request.user.profile.role != 'admin':
        return redirect('dashboard')
    
    # Platform stats
    from django.contrib.auth import get_user_model
    User = get_user_model()
    total_users = User.objects.count()
    new_users_this_month = User.objects.filter(
        date_joined__gte=timezone.now().replace(day=1)
    ).count()
    
    # Active sessions
    active_sessions = Session.objects.filter(state='active').count()
    total_sessions_this_month = Session.objects.filter(
        created_at__gte=timezone.now().replace(day=1)
    ).count()
    
    # Platform revenue (session charges)
    platform_revenue = LedgerEntry.objects.filter(
        created_at__gte=timezone.now().replace(day=1),
        entry_type='session_charge'
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Pending payouts
    pending_payouts = LedgerEntry.objects.filter(
        entry_type='payout',
        created_at__gte=timezone.now().replace(day=1)
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    pending_payout_count = ReaderProfile.objects.filter(
        # Simplified; would check actual payout status
    ).count()
    
    # Pending reader onboarding
    pending_readers = ReaderProfile.objects.filter(
        is_verified=False
    ).select_related('user').order_by('created_at')[:10]
    
    # Flagged content
    from community.models import Flag
    flagged_items = Flag.objects.filter(
        status='pending'
    ).order_by('-created_at')[:10]
    
    # Recent refunds
    recent_refunds = LedgerEntry.objects.filter(
        entry_type='refund',
        created_at__gte=timezone.now() - timedelta(days=7)
    ).select_related('wallet__user', 'session').order_by('-created_at')[:10]
    
    context = {
        'total_users': total_users,
        'new_users_this_month': new_users_this_month,
        'active_sessions': active_sessions,
        'total_sessions_this_month': total_sessions_this_month,
        'platform_revenue': platform_revenue,
        'platform_fee_percent': 30,  # SoulSeer takes 30%, readers get 70%
        'pending_payouts': pending_payouts,
        'pending_payout_count': pending_payout_count,
        'pending_readers': pending_readers,
        'flagged_items': flagged_items,
        'recent_refunds': recent_refunds,
    }
    return render(request, 'core/admin_dashboard.html', context)


@login_required
def dashboard(request):
    """Role-based dashboard router."""
    profile = request.user.profile
    
    if profile.role == 'reader':
        return reader_dashboard(request)
    elif profile.role == 'admin':
        return admin_dashboard(request)
    else:  # client
        return client_dashboard(request)
