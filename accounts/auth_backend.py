"""
Auth0 JWT validation and user sync.
"""
import logging
from django.contrib.auth import get_user_model
from jose import jwt, JWTError
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


def verify_auth0_token(token):
    """Verify Auth0 JWT and return payload or None."""
    try:
        issuer = get_auth0_issuer()
        audience = get_auth0_audience()
        if not issuer or not audience:
            logger.warning("Auth0 issuer or audience not configured")
            return None
        jwks_url = f"{issuer.rstrip('/')}/.well-known/jwks.json"
        import requests
        jwks = requests.get(jwks_url).json()
        unverified_header = jwt.get_unverified_header(token)
        rsa_key = {}
        for key in jwks.get('keys', []):
            if key['kid'] == unverified_header.get('kid'):
                rsa_key = {
                    'kty': key['kty'],
                    'kid': key['kid'],
                    'use': key.get('use', 'sig'),
                    'n': key['n'],
                    'e': key['e'],
                }
                break
        if not rsa_key:
            return None
        from jose.backends.cryptography_backend import CryptographyRSAKey
        public_key = CryptographyRSAKey(rsa_key)
        payload = jwt.decode(
            token,
            public_key,
            algorithms=['RS256'],
            audience=audience,
            issuer=issuer,
        )
        return payload
    except (JWTError, Exception) as e:
        logger.debug("Token verification failed: %s", e)
        return None


def get_or_create_user_from_token(payload):
    """Create or update Django User from Auth0 JWT payload."""
    sub = payload.get('sub')
    if not sub:
        return None
    from .models import UserProfile
    email = payload.get('email') or payload.get('email_verified')
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
