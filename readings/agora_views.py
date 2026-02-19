from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Session
from wallets.models import Wallet


def _generate_rtc_token(channel_name, uid, expiry=3600):
    from django.conf import settings
    from agora_token_builder import RtcTokenBuilder
    import time
    app_id = settings.AGORA_APP_ID
    cert = settings.AGORA_CERTIFICATE
    if not app_id or not cert:
        return None
    privilege_expired_ts = int(time.time()) + expiry
    role = RtcTokenBuilder.Role_Publisher
    token = RtcTokenBuilder.buildTokenWithUid(app_id, cert, channel_name, uid, role, privilege_expired_ts)
    return token


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def agora_token(request, session_id):
    """Return short-lived Agora RTC token for session."""
    try:
        session = Session.objects.select_related('client', 'reader').get(pk=session_id)
    except Session.DoesNotExist:
        return Response({'error': 'Session not found'}, status=404)
    if request.user != session.client and request.user != session.reader:
        return Response({'error': 'Unauthorized'}, status=403)
    if session.state not in ('waiting', 'active'):
        return Response({'error': 'Session not active'}, status=400)
    if request.user == session.client:
        try:
            wallet = Wallet.objects.get(user=request.user)
            if wallet.balance < session.rate_per_minute:
                return Response({'error': 'Insufficient balance'}, status=400)
        except Wallet.DoesNotExist:
            return Response({'error': 'No wallet'}, status=400)
    channel = session.channel_name or f"session_{session.pk}"
    uid = request.user.id % (2**31)
    token = _generate_rtc_token(channel, uid)
    if not token:
        return Response({'error': 'Token generation failed'}, status=500)
    return Response({
        'token': token,
        'channel': channel,
        'uid': uid,
    })
