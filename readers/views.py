from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q, Avg, Count
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from .models import ReaderProfile, ReaderRate, ReaderAvailability, Review, Favorite
from accounts.decorators import require_role


def reader_list(request):
    qs = ReaderProfile.objects.all().select_related('user').prefetch_related('rates')
    specialty = request.GET.get('specialty', '').strip()
    modality = request.GET.get('modality', '')
    if specialty:
        qs = qs.filter(specialties__icontains=specialty)
    if modality:
        qs = qs.filter(rates__modality=modality).distinct()
    readers = qs
    return render(request, 'readers/list.html', {
        'readers': readers,
        'specialty_filter': specialty,
        'modality_filter': modality,
    })


def reader_profile(request, slug):
    reader = get_object_or_404(ReaderProfile.objects.select_related('user').prefetch_related('rates', 'availability'), slug=slug)
    reviews = Review.objects.filter(reader=reader).select_related('client').order_by('-created_at')[:10]
    review_stats = Review.objects.filter(reader=reader).aggregate(a=Avg('rating'), c=Count('id'))
    avg_rating = review_stats['a']
    review_count = review_stats['c'] or 0
    is_favorite = request.user.is_authenticated and Favorite.objects.filter(client=request.user, reader=reader).exists()
    return render(request, 'readers/profile.html', {'reader': reader, 'reviews': reviews, 'avg_rating': avg_rating, 'review_count': review_count, 'is_favorite': is_favorite})


@login_required
@require_role('reader')
def reader_availability(request):
    rp = getattr(request.user, 'reader_profile', None)
    if not rp:
        return redirect('profile')
    slots = ReaderAvailability.objects.filter(reader=rp).order_by('day_of_week', 'start_time')
    if request.method == 'POST':
        ReaderAvailability.objects.filter(reader=rp).delete()
        for i in range(7):
            start = request.POST.get(f'day_{i}_start')
            end = request.POST.get(f'day_{i}_end')
            if start and end:
                ReaderAvailability.objects.create(reader=rp, day_of_week=i, start_time=start, end_time=end)
        return redirect('reader_availability')
    days = [(0, 'Monday'), (1, 'Tuesday'), (2, 'Wednesday'), (3, 'Thursday'), (4, 'Friday'), (5, 'Saturday'), (6, 'Sunday')]
    return render(request, 'readers/availability.html', {'reader_profile': rp, 'slots': slots, 'days': days})


@login_required
@require_role('reader')
def reader_rates(request):
    rp = getattr(request.user, 'reader_profile', None)
    if not rp:
        return redirect('profile')
    rates_dict = {r.modality: r.rate_per_minute for r in rp.rates.all()}
    if request.method == 'POST':
        from decimal import Decimal
        for mod in ['text', 'voice', 'video']:
            val = request.POST.get(f'rate_{mod}')
            if val is not None:
                try:
                    rate_val = Decimal(val)
                    ReaderRate.objects.update_or_create(reader=rp, modality=mod, defaults={'rate_per_minute': rate_val})
                except Exception:
                    pass
        return redirect('reader_rates')
    return render(request, 'readers/rates.html', {'reader_profile': rp, 'rates': rates_dict})


@login_required
@require_POST
def toggle_favorite(request, slug):
    reader = get_object_or_404(ReaderProfile, slug=slug)
    fav, created = Favorite.objects.get_or_create(client=request.user, reader=reader)
    if not created:
        fav.delete()
    return redirect('reader_profile', slug=slug)


def book_reader(request, slug):
    return redirect('schedule')


@login_required
def stripe_connect_onboard(request):
    """Initiate Stripe Connect onboarding for a reader to receive payouts."""
    import stripe
    from django.conf import settings
    rp = getattr(request.user, 'reader_profile', None)
    if not rp:
        return redirect('profile')
    stripe.api_key = settings.STRIPE_SECRET_KEY
    if rp.stripe_connect_account_id:
        # Already has account — generate new onboarding link
        account_id = rp.stripe_connect_account_id
    else:
        account = stripe.Account.create(
            type='express',
            email=request.user.email or None,
            metadata={'user_id': str(request.user.id)},
        )
        account_id = account.id
        rp.stripe_connect_account_id = account_id
        rp.save(update_fields=['stripe_connect_account_id'])

    link = stripe.AccountLink.create(
        account=account_id,
        refresh_url=request.build_absolute_uri('/readers/me/connect/'),
        return_url=request.build_absolute_uri('/dashboard/reader/'),
        type='account_onboarding',
    )
    return redirect(link.url)
