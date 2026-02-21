"""
Auth0 JWT validation and user sync.
Uses rsa library + stdlib for JWKS verification without cryptography/cffi dependency.
"""
import base64
import json
import logging
import struct
import time
import requests as http_requests
import rsa
import rsa.pem
from django.contrib.auth import get_user_model
from django.conf import settings

logger = logging.getLogger(__name__)
User = get_user_model()


def get_auth0_issuer():
    domain = getattr(settings, 'AUTH0_DOMAIN', '').strip()
    if domain:
        return f"https://{domain}/"
    return ''


def get_auth0_audience():
    return getattr(settings, 'AUTH0_AUDIENCE', '').strip() or getattr(settings, 'AUTH0_IDENTIFIER', '').strip()


def _b64decode(s):
    """Base64url decode with padding."""
    s = s.replace('-', '+').replace('_', '/')
    pad = 4 - len(s) % 4
    if pad < 4:
        s += '=' * pad
    return base64.b64decode(s)


def _decode_jwt_payload(token):
    """Decode JWT payload without verification."""
    parts = token.split('.')
    if len(parts) != 3:
        return None, None
    try:
        header = json.loads(_b64decode(parts[0]))
        payload = json.loads(_b64decode(parts[1]))
        return header, payload
    except Exception:
        return None, None


def _get_rsa_public_key(kid):
    """Fetch JWKS and build RSA public key from n/e for given kid."""
    issuer = get_auth0_issuer()
    if not issuer:
        return None
    jwks_url = f"{issuer.rstrip('/')}/.well-known/jwks.json"
    try:
        resp = http_requests.get(jwks_url, timeout=10)
        jwks = resp.json()
        for key_data in jwks.get('keys', []):
            if key_data.get('kid') == kid:
                # Build RSA public key from n, e
                n_bytes = _b64decode(key_data['n'])
                e_bytes = _b64decode(key_data['e'])
                n = int.from_bytes(n_bytes, 'big')
                e = int.from_bytes(e_bytes, 'big')
                pub_key = rsa.PublicKey(n, e)
                return pub_key
    except Exception as e:
        logger.debug("JWKS fetch failed: %s", e)
    return None


def verify_auth0_token(token):
    """Verify Auth0 JWT and return payload or None."""
    try:
        issuer = get_auth0_issuer()
        audience = get_auth0_audience()
        if not issuer or not audience:
            logger.warning("Auth0 issuer or audience not configured")
            return None

        header, payload = _decode_jwt_payload(token)
        if not header or not payload:
            return None

        kid = header.get('kid')
        alg = header.get('alg', 'RS256')

        # Verify signature for RS256
        if alg == 'RS256':
            pub_key = _get_rsa_public_key(kid)
            if not pub_key:
                logger.debug("Could not get public key for kid=%s", kid)
                return None

            parts = token.split('.')
            message = f"{parts[0]}.{parts[1]}".encode('utf-8')
            sig = _b64decode(parts[2])
            try:
                rsa.verify(message, sig, pub_key)
            except rsa.pkcs1.VerificationError:
                logger.debug("JWT signature verification failed")
                return None

        # Validate claims
        now = int(time.time())
        if payload.get('exp', 0) < now:
            logger.debug("JWT expired")
            return None
        if payload.get('iss') != issuer:
            logger.debug("JWT issuer mismatch")
            return None
        aud = payload.get('aud', '')
        if isinstance(aud, list):
            if audience not in aud:
                logger.debug("JWT audience mismatch")
                return None
        elif aud != audience:
            logger.debug("JWT audience mismatch")
            return None

        return payload
    except Exception as e:
        logger.debug("Token verification failed: %s", e)
        return None


def get_or_create_user_from_token(payload):
    """Create or update Django User from Auth0 JWT payload."""
    sub = payload.get('sub')
    if not sub:
        return None
    from .models import UserProfile
    email = payload.get('email')
    if isinstance(email, bool):
        email = None
    name = payload.get('name') or payload.get('nickname', '')
    parts = name.split(maxsplit=1) if name else ['']
    first_name = parts[0] if parts else ''
    last_name = parts[1] if len(parts) > 1 else ''
    username = f"auth0_{sub.replace('|', '_')}"[:150]
    user, created = User.objects.get_or_create(
        username=username,
        defaults={
            'email': email or '',
            'first_name': first_name,
            'last_name': last_name,
        }
    )
    if not created:
        if email:
            user.email = email
        user.first_name = first_name
        user.last_name = last_name
        user.save(update_fields=['email', 'first_name', 'last_name'])
    profile, _ = UserProfile.objects.get_or_create(
        user=user,
        defaults={'auth0_sub': sub, 'role': 'client'}
    )
    if profile.auth0_sub != sub:
        profile.auth0_sub = sub
        profile.save(update_fields=['auth0_sub'])
    return user
