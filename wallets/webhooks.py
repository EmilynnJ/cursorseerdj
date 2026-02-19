import stripe
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib.auth import get_user_model

from .models import Wallet, LedgerEntry, ProcessedStripeEvent

User = get_user_model()
stripe.api_key = settings.STRIPE_SECRET_KEY


def _get_payload(request):
    import json
    return json.loads(request.body)


@csrf_exempt
@require_POST
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        return HttpResponse(status=400)
    except stripe.SignatureVerificationError:
        return HttpResponse(status=400)

    event_id = event.get('id')
    if ProcessedStripeEvent.objects.filter(stripe_event_id=event_id).exists():
        return HttpResponse(status=200)

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        meta = session.get('metadata', {})
        if meta.get('product_id'):
            from shop.models import Product, Order, OrderItem
            user_id, product_id = meta.get('user_id'), meta.get('product_id')
            if user_id and product_id:
                try:
                    user = User.objects.get(pk=user_id)
                    product = Product.objects.get(pk=product_id)
                    order = Order.objects.create(user=user, stripe_checkout_session_id=session.get('id', ''), status='paid')
                    OrderItem.objects.create(order=order, product=product, quantity=1)
                except Exception:
                    pass
            ProcessedStripeEvent.objects.create(stripe_event_id=event_id)
            return HttpResponse(status=200)
        if meta.get('type') == 'wallet_topup':
            user_id = meta.get('user_id')
            payment_intent_id = session.get('payment_intent') or session.get('id', '')
            amount_total = session.get('amount_total', 0)
            if user_id and amount_total:
                from decimal import Decimal
                amount = Decimal(amount_total) / 100
                idempotency_key = f"topup_{session.get('id', event_id)}"
                try:
                    user = User.objects.get(pk=user_id)
                    wallet, _ = Wallet.objects.get_or_create(user=user, defaults={})
                    from .models import credit_wallet
                    credit_wallet(
                        wallet,
                        amount,
                        'top_up',
                        idempotency_key,
                        stripe_payment_intent_id=payment_intent_id or '',
                        stripe_event_id=event_id,
                    )
                except Exception:
                    pass
        ProcessedStripeEvent.objects.create(stripe_event_id=event_id)
        return HttpResponse(status=200)

    if event['type'] == 'payment_intent.succeeded':
        pi = event['data']['object']
        metadata = pi.get('metadata', {})
        if metadata.get('type') == 'wallet_topup':
            user_id = metadata.get('user_id')
            amount_total = pi.get('amount', 0)
            if user_id and amount_total:
                from decimal import Decimal
                amount = Decimal(amount_total) / 100
                idempotency_key = f"topup_{pi['id']}"
                try:
                    user = User.objects.get(pk=user_id)
                    wallet, _ = Wallet.objects.get_or_create(user=user, defaults={})
                    from .models import credit_wallet
                    credit_wallet(
                        wallet,
                        amount,
                        'top_up',
                        idempotency_key,
                        stripe_payment_intent_id=pi['id'],
                        stripe_event_id=event_id,
                    )
                except Exception:
                    pass
        ProcessedStripeEvent.objects.create(stripe_event_id=event_id)
        return HttpResponse(status=200)

    ProcessedStripeEvent.objects.create(stripe_event_id=event_id)
    return HttpResponse(status=200)
