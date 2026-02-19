from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, Http404
from django.utils import timezone
from datetime import timedelta
from .models import Product, Order, OrderItem
from .storage import generate_signed_url


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


@login_required
def digital_download(request, order_item_id):
    """Serve digital product download with signed URL."""
    order_item = get_object_or_404(
        OrderItem.objects.select_related('order', 'product'),
        pk=order_item_id,
        order__user=request.user
    )
    
    # Check if product is digital
    if order_item.product.type != 'digital':
        raise Http404("Not a digital product")
    
    # Check if order is paid
    if order_item.order.status != 'paid':
        return HttpResponse("Order not yet paid", status=403)
    
    # Generate signed URL if not already generated or expired
    if not order_item.delivery_url or order_item.delivery_expires_at < timezone.now():
        if order_item.product.file:
            signed_url = generate_signed_url(order_item.product.file, expiration_hours=24)
            if signed_url:
                order_item.delivery_url = signed_url
                order_item.delivery_expires_at = timezone.now() + timedelta(hours=24)
                order_item.save(update_fields=['delivery_url', 'delivery_expires_at'])
    
    if order_item.delivery_url:
        return redirect(order_item.delivery_url)
    else:
        return HttpResponse("Download not available", status=404)
