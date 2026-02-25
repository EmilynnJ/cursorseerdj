"""
Agora RTC/RTM integration for voice/video sessions and livestream.
Handles token generation, channel management, and real-time features.
"""

import json
import logging
from datetime import datetime, timedelta
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods, require_POST
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.conf import settings
from .agora_token import RtcTokenBuilder, ROLE_PUBLISHER, ROLE_SUBSCRIBER
from .models import Session
from wallets.models import Wallet

logger = logging.getLogger(__name__)

# ============================================================================
# RTC TOKEN GENERATION (Voice/Video Sessions)
# ============================================================================

@login_required
@require_POST
def get_rtc_token(request, session_id):
    """
    Generate Agora RTC token for session access.
    
    POST /api/sessions/{session_id}/rtc-token/
    Returns: {token: "...", channel: "...", uid: user.id, expireTime: 1200}
    
    Security:
    - Verify session exists and user is participant
    - Verify session is in 'active' or 'waiting' state
    - Verify wallet has sufficient balance
    - Generate short-lived token (1200s = 20 min)
    """
    try:
        session = get_object_or_404(Session, pk=session_id)
        
        # Verify user is client or reader
        if request.user not in [session.client, session.reader]:
            return JsonResponse({'error': 'Unauthorized'}, status=403)
        
        # Verify session is active or waiting
        if session.state not in ['active', 'waiting']:
            return JsonResponse({'error': f'Session not active (state={session.state})'}, status=400)
        
        # For client: verify wallet has balance
        if request.user == session.client:
            wallet = Wallet.objects.get(user=session.client)
            if wallet.balance < session.rate_per_minute:
                return JsonResponse({'error': 'Insufficient balance'}, status=402)
        
        # Ensure channel name exists
        if not session.channel_name:
            session.channel_name = f"session_{session.id}_{int(timezone.now().timestamp())}"
            session.save()
        
        # Generate RTC token
        privilege_expire_ts = int(timezone.now().timestamp()) + 1200
        token = RtcTokenBuilder.build_token_with_uid(
            app_id=settings.AGORA_APP_ID,
            app_certificate=settings.AGORA_CERTIFICATE,
            channel_name=session.channel_name,
            uid=request.user.id,
            role=ROLE_PUBLISHER,
            privilege_expire_ts=privilege_expire_ts,
        )
        
        logger.info(f"RTC token generated for session {session_id}, user {request.user.id}")
        
        return JsonResponse({
            'token': token,
            'channel': session.channel_name,
            'uid': request.user.id,
            'expireTime': 1200,
            'appId': settings.AGORA_APP_ID,
        })
    except Session.DoesNotExist:
        return JsonResponse({'error': 'Session not found'}, status=404)
    except Wallet.DoesNotExist:
        return JsonResponse({'error': 'Wallet not found'}, status=404)
    except Exception as e:
        logger.error(f"RTC token generation error: {e}")
        return JsonResponse({'error': str(e)}, status=500)


# ============================================================================
# SESSION MANAGEMENT (Join/Leave/Reconnect)
# ============================================================================

@login_required
@require_POST
def session_join(request, session_id):
    """
    Client/reader joins session. Transitions to 'active', generates channel & token.
    
    POST /api/sessions/{session_id}/join/
    """
    try:
        session = get_object_or_404(Session, pk=session_id)
        
        # Verify user is participant
        if request.user not in [session.client, session.reader]:
            return JsonResponse({'error': 'Unauthorized'}, status=403)
        
        # Verify session state
        if session.state not in ['waiting', 'paused']:
            return JsonResponse({'error': f'Cannot join from state {session.state}'}, status=400)
        
        # For client: verify balance
        if request.user == session.client:
            wallet = Wallet.objects.get(user=session.client)
            if wallet.balance < session.rate_per_minute:
                return JsonResponse({'error': 'Insufficient balance'}, status=402)
        
        # Generate Agora channel name if not exists
        if not session.channel_name:
            session.channel_name = f"session_{session.id}_{int(timezone.now().timestamp())}"
        
        # Set started_at on first join
        if not session.started_at:
            session.started_at = timezone.now()
        
        # Clear grace_until if reconnecting
        session.grace_until = None
        
        # Transition to active
        if not session.transition('active'):
            return JsonResponse({'error': 'Invalid state transition'}, status=400)
        
        session.save()
        logger.info(f"Session {session_id} joined by user {request.user.id}")
        
        # Generate token
        privilege_expire_ts = int(timezone.now().timestamp()) + 1200
        token = RtcTokenBuilder.build_token_with_uid(
            app_id=settings.AGORA_APP_ID,
            app_certificate=settings.AGORA_CERTIFICATE,
            channel_name=session.channel_name,
            uid=request.user.id,
            role=ROLE_PUBLISHER,
            privilege_expire_ts=privilege_expire_ts,
        )
        
        return JsonResponse({
            'success': True,
            'token': token,
            'channel': session.channel_name,
            'uid': request.user.id,
            'appId': settings.AGORA_APP_ID,
        })
    except Session.DoesNotExist:
        return JsonResponse({'error': 'Session not found'}, status=404)
    except Exception as e:
        logger.error(f"Session join error: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_POST
def session_leave(request, session_id):
    """
    Client/reader leaves session (disconnect).
    
    POST /api/sessions/{session_id}/leave/
    """
    try:
        session = get_object_or_404(Session, pk=session_id)
        
        if request.user not in [session.client, session.reader]:
            return JsonResponse({'error': 'Unauthorized'}, status=403)
        
        if session.state not in ['active', 'paused']:
            return JsonResponse({'error': f'Cannot leave from state {session.state}'}, status=400)
        
        # Set grace period (5 minutes)
        session.grace_until = timezone.now() + timedelta(minutes=5)
        session.reconnect_count += 1
        
        # Transition to paused (allow reconnect)
        if not session.transition('paused'):
            return JsonResponse({'error': 'Invalid state transition'}, status=400)
        
        session.save()
        logger.info(f"Session {session_id} left by user {request.user.id}, grace until {session.grace_until}")
        
        return JsonResponse({
            'success': True,
            'state': session.state,
            'graceUntil': session.grace_until.isoformat(),
            'reconnectCount': session.reconnect_count,
        })
    except Session.DoesNotExist:
        return JsonResponse({'error': 'Session not found'}, status=404)
    except Exception as e:
        logger.error(f"Session leave error: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_POST
def session_reconnect(request, session_id):
    """
    Client/reader reconnects within grace period.
    
    POST /api/sessions/{session_id}/reconnect/
    """
    try:
        session = get_object_or_404(Session, pk=session_id)
        
        if request.user not in [session.client, session.reader]:
            return JsonResponse({'error': 'Unauthorized'}, status=403)
        
        if session.state != 'paused':
            return JsonResponse({'error': f'Can only reconnect from paused state'}, status=400)
        
        # Check grace period
        if not session.grace_until or timezone.now() > session.grace_until:
            return JsonResponse({'error': 'Reconnect grace period expired'}, status=410)
        
        # For client: verify balance still exists
        if request.user == session.client:
            wallet = Wallet.objects.get(user=session.client)
            if wallet.balance < session.rate_per_minute:
                return JsonResponse({'error': 'Insufficient balance for reconnect'}, status=402)
        
        # Transition back to active
        if not session.transition('active'):
            return JsonResponse({'error': 'Invalid state transition'}, status=400)
        
        session.grace_until = None
        session.save()
        logger.info(f"Session {session_id} reconnected by user {request.user.id}")
        
        # Generate new token
        privilege_expire_ts = int(timezone.now().timestamp()) + 1200
        token = RtcTokenBuilder.build_token_with_uid(
            app_id=settings.AGORA_APP_ID,
            app_certificate=settings.AGORA_CERTIFICATE,
            channel_name=session.channel_name,
            uid=request.user.id,
            role=ROLE_PUBLISHER,
            privilege_expire_ts=privilege_expire_ts,
        )
        
        return JsonResponse({
            'success': True,
            'token': token,
            'channel': session.channel_name,
            'uid': request.user.id,
        })
    except Session.DoesNotExist:
        return JsonResponse({'error': 'Session not found'}, status=404)
    except Exception as e:
        logger.error(f"Session reconnect error: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_POST
def session_end(request, session_id):
    """
    End session explicitly.
    
    POST /api/sessions/{session_id}/end/
    """
    try:
        session = get_object_or_404(Session, pk=session_id)
        
        if request.user not in [session.client, session.reader]:
            return JsonResponse({'error': 'Unauthorized'}, status=403)
        
        if session.state not in ['active', 'paused', 'reconnecting']:
            return JsonResponse({'error': f'Cannot end from state {session.state}'}, status=400)
        
        # Record summary if provided
        summary = request.POST.get('summary', '')
        if summary:
            session.summary = summary[:1000]
        
        # Set ended_at
        session.ended_at = timezone.now()
        
        # Transition to ended
        if not session.transition('ended'):
            return JsonResponse({'error': 'Invalid state transition'}, status=400)
        
        session.save()
        logger.info(f"Session {session_id} ended by user {request.user.id}")
        
        # Queue finalization task
        from readings.tasks import session_finalize
        session_finalize.delay(session_id)
        
        return JsonResponse({
            'success': True,
            'state': session.state,
            'endedAt': session.ended_at.isoformat(),
            'billingMinutes': session.billing_minutes,
            'totalCharge': float(session.rate_per_minute * session.billing_minutes),
        })
    except Session.DoesNotExist:
        return JsonResponse({'error': 'Session not found'}, status=404)
    except Exception as e:
        logger.error(f"Session end error: {e}")
        return JsonResponse({'error': str(e)}, status=500)


# ============================================================================
# LIVESTREAM RTC TOKEN
# ============================================================================

@login_required
@require_POST
def get_livestream_token(request, livestream_id):
    """
    Generate RTC token for livestream viewing/hosting.
    
    POST /api/live/{livestream_id}/token/
    """
    from live.models import Livestream
    
    try:
        livestream = get_object_or_404(Livestream, pk=livestream_id)
        
        # Verify livestream is active
        if not livestream.started_at or livestream.ended_at:
            return JsonResponse({'error': 'Livestream not active'}, status=400)
        
        # Check visibility
        if livestream.visibility == 'premium':
            # Premium streams require authentication and a minimum wallet balance ($1.00)
            if request.user != livestream.reader:
                try:
                    wallet = Wallet.objects.get(user=request.user)
                    if wallet.balance < 1:
                        return JsonResponse({'error': 'Premium stream: insufficient wallet balance'}, status=402)
                except Wallet.DoesNotExist:
                    return JsonResponse({'error': 'Premium stream: wallet required'}, status=402)
        elif livestream.visibility == 'private':
            if request.user != livestream.reader:
                return JsonResponse({'error': 'Private livestream'}, status=403)
        
        # Determine role: host if reader, audience if viewer
        role = 1 if request.user == livestream.reader else 0
        
        privilege_expire_ts = int(timezone.now().timestamp()) + 3600
        ls_role = ROLE_PUBLISHER if request.user == livestream.reader else ROLE_SUBSCRIBER
        token = RtcTokenBuilder.build_token_with_uid(
            app_id=settings.AGORA_APP_ID,
            app_certificate=settings.AGORA_CERTIFICATE,
            channel_name=livestream.agora_channel,
            uid=request.user.id,
            role=ls_role,
            privilege_expire_ts=privilege_expire_ts,
        )
        
        return JsonResponse({
            'token': token,
            'channel': livestream.agora_channel,
            'uid': request.user.id,
            'appId': settings.AGORA_APP_ID,
        })
    except Livestream.DoesNotExist:
        return JsonResponse({'error': 'Livestream not found'}, status=404)
    except Exception as e:
        logger.error(f"Livestream token error: {e}")
        return JsonResponse({'error': str(e)}, status=500)
