from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Product, Order, OrderItem


def shop_list(request):
    products = Product.objects.all()
    return render(request, 'shop/list.html', {'products': products})


@login_required
def checkout_start(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    import stripe
    from django.conf import settings
    stripe.api_key = settings.STRIPE_SECRET_KEY
    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price_data': {
                'currency': 'usd',
                'product_data': {'name': product.name},
                'unit_amount': int(product.price * 100),
            },
            'quantity': 1,
        }],
        mode='payment',
        success_url=request.build_absolute_uri('/shop/orders/'),
        cancel_url=request.build_absolute_uri('/shop/'),
        metadata={'user_id': str(request.user.id), 'product_id': str(product.id)},
    )
    return redirect(session.url)


@login_required
def order_list(request):
    orders = Order.objects.filter(user=request.user).prefetch_related('items__product').order_by('-created_at')
    return render(request, 'shop/orders.html', {'orders': orders})
