from django.urls import path
from . import views

urlpatterns = [
    path('', views.forum_list, name='community_forum'),
    path('thread/<int:pk>/', views.thread_detail, name='thread_detail'),
    path('category/<int:category_id>/new/', views.create_thread, name='create_thread'),
    path('thread/<int:thread_id>/reply/', views.reply, name='thread_reply'),
    path('flag/', views.flag_content, name='flag_content'),
]
