from django.urls import path
from . import views

urlpatterns = [
    path('', views.inbox, name='messages_inbox'),
    path('start/<int:reader_id>/', views.start_conversation, name='start_conversation'),
    path('<int:pk>/', views.conversation_detail, name='conversation_detail'),
    path('<int:conv_id>/send/', views.send_message, name='send_message'),
]
