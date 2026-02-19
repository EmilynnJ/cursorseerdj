import stripe
from django.conf import settings


def get_or_create_stripe_customer(user):
    """Get or create Stripe customer for user."""
    stripe.api_key = settings.STRIPE_SECRET_KEY
    from .models import Wallet
    wallet, _ = Wallet.objects.get_or_create(user=user, defaults={})
    if wallet.stripe_customer_id:
        return wallet.stripe_customer_id
    customer = stripe.Customer.create(
        email=user.email or None,
        metadata={'user_id': str(user.id)},
    )
    wallet.stripe_customer_id = customer.id
    wallet.save(update_fields=['stripe_customer_id'])
    return customer.id


def create_checkout_session(user, amount_cents, success_url, cancel_url):
    """Create Stripe Checkout Session for wallet top-up."""
    stripe.api_key = settings.STRIPE_SECRET_KEY
    customer_id = get_or_create_stripe_customer(user)
    session = stripe.checkout.Session.create(
        customer=customer_id,
        payment_method_types=['card'],
        line_items=[{
            'price_data': {
                'currency': 'usd',
                'product_data': {'name': 'SoulSeer Wallet Top-Up'},
                'unit_amount': amount_cents,
            },
            'quantity': 1,
        }],
        mode='payment',
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={'user_id': str(user.id), 'type': 'wallet_topup'},
    )
    return session
