from decimal import Decimal
from django.conf import settings
from django.db import models

PRODUCT_TYPE = [
    ('digital', 'Digital'),
    ('physical', 'Physical'),
]


class Product(models.Model):
    stripe_product_id = models.CharField(max_length=255, blank=True, db_index=True)
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=20, choices=PRODUCT_TYPE, default='physical')
    price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0'))
    file = models.CharField(max_length=500, blank=True, help_text='R2 key for digital')


class Order(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='orders',
    )
    stripe_checkout_session_id = models.CharField(max_length=255, blank=True, db_index=True)
    status = models.CharField(max_length=50, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    delivery_url = models.URLField(blank=True, help_text='Signed URL for digital delivery')
