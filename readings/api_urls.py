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

    # Session lifecycle (API - prefixed with api_ to avoid name collision with HTML views)
    path('sessions/<int:session_id>/join/', session_join, name='api_session_join'),
    path('sessions/<int:session_id>/leave/', session_leave, name='api_session_leave'),
    path('sessions/<int:session_id>/reconnect/', session_reconnect, name='api_session_reconnect'),
    path('sessions/<int:session_id>/end/', session_end, name='api_session_end'),

    # Livestream RTC token generation
    path('livestreams/<int:livestream_id>/rtc-token/', get_livestream_token, name='get_livestream_token'),
]
