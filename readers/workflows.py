# Reader profile, booking, and livestream workflows

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Avg, Count
from django.utils import timezone
from django.http import JsonResponse
from django import forms
import json

from readers.models import ReaderProfile, ReaderRate, ReaderAvailability, Review, Favorite
from scheduling.models import ScheduledSlot, Booking
from readings.models import Session
from wallets.models import Wallet, debit_wallet
from live.models import Livestream, Gift, GiftPurchase
from decimal import Decimal


def browse_readers(request):
    """Browse and filter readers."""
    readers = ReaderProfile.objects.filter(is_verified=True).select_related('user')
    
    # Filters
    modality = request.GET.get('modality')
    price = request.GET.get('price')
    rating = request.GET.get('rating')
    q = request.GET.get('q')
    sort = request.GET.get('sort', 'featured')
    
    if modality:
        readers = readers.filter(rates__modality=modality)
    
    if price:
        if price == 'under-2':
            readers = readers.filter(rates__rate_per_minute__lt=2)
        elif price == '2-5':
            readers = readers.filter(rates__rate_per_minute__gte=2, rates__rate_per_minute__lt=5)
        elif price == '5-10':
            readers = readers.filter(rates__rate_per_minute__gte=5, rates__rate_per_minute__lt=10)
        elif price == 'over-10':
            readers = readers.filter(rates__rate_per_minute__gte=10)
    
    if rating:
        rating_val = float(rating)
        readers = readers.annotate(avg_rating=Avg('reviews__rating')).filter(avg_rating__gte=rating_val)
    
    if q:
        readers = readers.filter(Q(user__profile__display_name__icontains=q) | Q(specialties__icontains=q))
    
    # Sort
    if sort == 'rating':
        readers = readers.annotate(avg_rating=Avg('reviews__rating')).order_by('-avg_rating')
    elif sort == 'price_low':
        readers = readers.annotate(min_rate=Min('rates__rate_per_minute')).order_by('min_rate')
    elif sort == 'reviews':
        readers = readers.annotate(review_count=Count('reviews')).order_by('-review_count')
    
    # Add computed fields
    for reader in readers:
        reader.avg_rating = reader.reviews.aggregate(avg=Avg('rating'))['avg'] or 0
        reader.review_count = reader.reviews.count()
        rates = ReaderRate.objects.filter(reader=reader)
        reader.rates = {r.modality: r.rate_per_minute for r in rates}
    
    return render(request, 'readers/browse.html', {'readers': readers})


def reader_detail(request, slug):
    """Reader profile detail with reviews, rates, availability."""
    reader = get_object_or_404(ReaderProfile, slug=slug)
    
    reviews = Review.objects.filter(reader=reader).select_related('client')
    avg_rating = reviews.aggregate(avg=Avg('rating'))['avg'] or 0
    
    rates = ReaderRate.objects.filter(reader=reader)
    
    availability = ReaderAvailability.objects.filter(reader=reader)
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    availability_by_day = []
    for day_num in range(7):
        day_avail = availability.filter(day_of_week=day_num).first()
        status = f"{day_avail.start_time.strftime('%H:%M')} - {day_avail.end_time.strftime('%H:%M')}" if day_avail else "Not Available"
        availability_by_day.append((days[day_num], status))
    
    # Check if favorited
    is_favorited = False
    if request.user.is_authenticated:
        is_favorited = Favorite.objects.filter(
            client=request.user,
            reader=reader
        ).exists()
    
    context = {
        'reader': reader,
        'reviews': reviews,
        'avg_rating': avg_rating,
        'rates': rates,
        'availability_by_day': availability_by_day,
        'is_favorited': is_favorited,
    }
    return render(request, 'readers/detail.html', context)


@login_required
def book_reader(request, slug):
    """Start session booking flow."""
    reader = get_object_or_404(ReaderProfile, slug=slug)
    rates = ReaderRate.objects.filter(reader=reader)
    
    if request.method == 'POST':
        modality = request.POST.get('modality')
        rate_obj = rates.get(modality=modality)
        
        # Check wallet balance
        wallet = Wallet.objects.get(user=request.user)
        if wallet.balance < rate_obj.rate_per_minute:
            return redirect('wallet_topup')
        
        # Create session
        session = Session.objects.create(
            client=request.user,
            reader=reader,
            modality=modality,
            state='created',
            rate_per_minute=rate_obj.rate_per_minute,
        )
        
        return redirect('session_join', session_id=session.id)
    
    context = {
        'reader': reader,
        'rates': rates,
    }
    return render(request, 'readers/book.html', context)


@login_required
def toggle_favorite(request, reader_id):
    """Add/remove reader from favorites."""
    reader = get_object_or_404(ReaderProfile, id=reader_id)
    favorite, created = Favorite.objects.get_or_create(
        client=request.user,
        reader=reader
    )
    
    if not created:
        favorite.delete()
        return JsonResponse({'favorited': False})
    
    return JsonResponse({'favorited': True})


@login_required
def edit_reader_availability(request):
    """Edit weekly availability."""
    reader = ReaderProfile.objects.get(user=request.user)
    availability = ReaderAvailability.objects.filter(reader=reader)
    
    if request.method == 'POST':
        for day_num in range(7):
            enabled = request.POST.get(f'day_{day_num}_enabled') == 'on'
            if enabled:
                start_time = request.POST.get(f'day_{day_num}_start')
                end_time = request.POST.get(f'day_{day_num}_end')
                
                ReaderAvailability.objects.update_or_create(
                    reader=reader,
                    day_of_week=day_num,
                    defaults={'start_time': start_time, 'end_time': end_time}
                )
            else:
                ReaderAvailability.objects.filter(
                    reader=reader,
                    day_of_week=day_num
                ).delete()
        
        return redirect('reader_dashboard')
    
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    availability_data = []
    for day_num in range(7):
        day_avail = availability.filter(day_of_week=day_num).first()
        availability_data.append({
            'day': days[day_num],
            'day_num': day_num,
            'slots': [day_avail] if day_avail else []
        })
    
    context = {
        'availability_data': availability_data,
    }
    return render(request, 'readers/availability.html', context)


@login_required
def browse_livestreams(request):
    """Browse active livestreams."""
    livestreams = Livestream.objects.filter(
        is_live=True
    ).select_related('reader').order_by('-started_at')
    
    # Filter by visibility
    user_livestreams = livestreams.filter(
        Q(visibility='public') |
        Q(visibility='private', viewers__user=request.user) |
        Q(visibility='premium', viewers__user__subscription__is_active=True)
    ).distinct()
    
    context = {
        'livestreams': user_livestreams,
    }
    return render(request, 'live/livestreams.html', context)


@login_required
def join_livestream(request, livestream_id):
    """Join livestream with Agora RTC."""
    livestream = get_object_or_404(Livestream, id=livestream_id)
    
    # Check visibility
    if livestream.visibility == 'private' and request.user not in livestream.viewers.all():
        return redirect('browse_livestreams')
    
    if livestream.visibility == 'premium':
        # Check subscription (simplified)
        has_subscription = hasattr(request.user, 'subscription') and request.user.subscription.is_active
        if not has_subscription:
            return redirect('upgrade_subscription')
    
    context = {
        'livestream': livestream,
        'AGORA_APP_ID': settings.AGORA_APP_ID,
        'available_gifts': Gift.objects.all(),
    }
    return render(request, 'live/livestream.html', context)


@login_required
def send_gift(request):
    """Send gift to livestream reader."""
    if request.method == 'POST':
        data = json.loads(request.body)
        livestream_id = data.get('livestream_id')
        gift_id = data.get('gift_id')
        
        livestream = get_object_or_404(Livestream, id=livestream_id)
        gift = get_object_or_404(Gift, id=gift_id)
        
        # Charge wallet
        wallet = Wallet.objects.get(user=request.user)
        try:
            debit_wallet(
                wallet,
                Decimal(str(gift.price)),
                'gift',
                f"gift_{livestream.id}_{gift.id}_{request.user.id}_{timezone.now().timestamp()}",
                reference_type='livestream',
                reference_id=str(livestream.id)
            )
        except ValueError:
            return JsonResponse({'success': False, 'error': 'Insufficient balance'})
        
        # Create gift purchase (70% to reader, 30% to platform)
        from wallets.models import LedgerEntry
        reader_amount = Decimal(str(gift.price)) * Decimal('0.7')
        platform_amount = Decimal(str(gift.price)) * Decimal('0.3')
        
        GiftPurchase.objects.create(
            livestream=livestream,
            sender=request.user,
            gift=gift,
            amount=gift.price,
        )
        
        # Credit reader wallet with 70%
        reader_wallet = Wallet.objects.get(user=livestream.reader.user)
        LedgerEntry.objects.create(
            wallet=reader_wallet,
            amount=reader_amount,
            entry_type='commission',
            reference_type='gift',
            reference_id=str(livestream.id)
        )
        reader_wallet.refresh_from_db()
        
        return JsonResponse({'success': True})
    
    return JsonResponse({'success': False}, status=400)
