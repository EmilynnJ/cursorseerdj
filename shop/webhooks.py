import stripe
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

stripe.api_key = settings.STRIPE_SECRET_KEY


@csrf_exempt
@require_POST
def shop_webhook(request):
    payload = request.body
    sig = request.META.get('HTTP_STRIPE_SIGNATURE', '')
    try:
        event = stripe.Webhook.construct_event(payload, sig, settings.STRIPE_WEBHOOK_SECRET)
    except (ValueError, stripe.SignatureVerificationError):
        return HttpResponse(status=400)
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        meta = session.get('metadata', {})
        user_id = meta.get('user_id')
        product_id = meta.get('product_id')
        if user_id and product_id:
            from django.contrib.auth import get_user_model
            from .models import Product, Order, OrderItem
            User = get_user_model()
            try:
                user = User.objects.get(pk=user_id)
                product = Product.objects.get(pk=product_id)
                order = Order.objects.create(
                    user=user,
                    stripe_checkout_session_id=session.get('id', ''),
                    status='paid',
                )
                OrderItem.objects.create(order=order, product=product, quantity=1)
            except Exception:
                pass
    return HttpResponse(status=200)
