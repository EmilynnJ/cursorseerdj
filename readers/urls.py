from django.urls import path
from . import views

urlpatterns = [
    path('', views.reader_list, name='reader_list'),
    path('me/availability/', views.reader_availability, name='reader_availability'),
    path('me/rates/', views.reader_rates, name='reader_rates'),
    path('me/connect/', views.stripe_connect_onboard, name='stripe_connect_onboard'),
    path('<slug:slug>/', views.reader_profile, name='reader_profile'),
    path('<slug:slug>/favorite/', views.toggle_favorite, name='toggle_favorite'),
    path('<slug:slug>/book/', views.book_reader, name='book_reader'),
]
