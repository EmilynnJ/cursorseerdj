from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Session
from readers.models import ReaderProfile, ReaderRate


@login_required
def create_session(request, reader_id):
    reader = get_object_or_404(ReaderProfile, pk=reader_id)
    rate = ReaderRate.objects.filter(reader=reader, modality='voice').first()
    if not rate:
        rate = reader.rates.first()
    rpm = rate.rate_per_minute if rate else 0
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
    return render(request, 'readings/session.html', {'session': session})
