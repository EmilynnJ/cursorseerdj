from django.urls import path
from .agora_views import (
    get_rtc_token, 
    session_join, 
    session_leave, 
    session_reconnect,
    session_end,
    get_livestream_token,
)

urlpatterns = [
    # Session RTC token generation
    path('sessions/<int:session_id>/rtc-token/', get_rtc_token, name='get_rtc_token'),
    
    # Session lifecycle
    path('sessions/<int:session_id>/join/', session_join, name='session_join'),
    path('sessions/<int:session_id>/leave/', session_leave, name='session_leave'),
    path('sessions/<int:session_id>/reconnect/', session_reconnect, name='session_reconnect'),
    path('sessions/<int:session_id>/end/', session_end, name='session_end'),
    
    # Livestream RTC token generation
    path('livestreams/<int:livestream_id>/rtc-token/', get_livestream_token, name='get_livestream_token'),
]
