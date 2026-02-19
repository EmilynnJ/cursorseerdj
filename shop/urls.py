from django.urls import path
from . import views

urlpatterns = [
    path('', views.shop_list, name='shop_list'),
    path('checkout/<int:product_id>/', views.checkout_start, name='shop_checkout'),
    path('orders/', views.order_list, name='shop_orders'),
]
