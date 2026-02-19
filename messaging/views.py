from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import Conversation, Message


@login_required
def start_conversation(request, reader_id):
    from django.contrib.auth import get_user_model
    from readers.models import ReaderProfile
    User = get_user_model()
    reader_user = get_object_or_404(User, pk=reader_id)
    rp = ReaderProfile.objects.filter(user=reader_user).first()
    if not rp:
        return redirect('messages_inbox')
    conv, _ = Conversation.objects.get_or_create(client=request.user, reader=reader_user)
    return redirect('conversation_detail', pk=conv.pk)


@login_required
def inbox(request):
    if hasattr(request.user, 'profile') and request.user.profile.role == 'reader':
        convos = Conversation.objects.filter(reader=request.user).select_related('client', 'reader').order_by('-updated_at')
    else:
        convos = Conversation.objects.filter(client=request.user).select_related('client', 'reader').order_by('-updated_at')
    return render(request, 'messaging/inbox.html', {'conversations': convos})


@login_required
def conversation_detail(request, pk):
    conv = get_object_or_404(Conversation.objects.select_related('client', 'reader'), pk=pk)
    if request.user != conv.client and request.user != conv.reader:
        return redirect('messages_inbox')
    messages = conv.messages.select_related('sender').order_by('created_at')
    return render(request, 'messaging/conversation.html', {'conversation': conv, 'messages': messages})


@login_required
@require_POST
def send_message(request, conv_id):
    conv = get_object_or_404(Conversation, pk=conv_id)
    if request.user != conv.client and request.user != conv.reader:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    body = request.POST.get('body', '').strip()
    if not body:
        return JsonResponse({'error': 'Empty message'}, status=400)
    is_paid = request.POST.get('is_paid') == '1'
    if is_paid and request.user == conv.reader:
        from wallets.models import Wallet, debit_wallet
        try:
            wallet = Wallet.objects.get(user=conv.client)
            amount = 1
            idem = f"paid_reply_{conv_id}_{Message.objects.filter(conversation=conv).count()}"
            debit_wallet(wallet, amount, 'paid_reply', idem, reference_type='paid_reply', reference_id=str(conv_id))
            entry = wallet.entries.get(idempotency_key=idem)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    else:
        entry = None
        is_paid = False
    msg = Message.objects.create(
        conversation=conv,
        sender=request.user,
        body=body,
        is_paid_reply=is_paid,
        ledger_entry=entry,
    )
    conv.save()
    return redirect('conversation_detail', pk=conv_id)
