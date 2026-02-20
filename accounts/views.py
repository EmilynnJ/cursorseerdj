import secrets
import requests as http_requests
from django.shortcuts import render, redirect
from django.conf import settings
from .auth_backend import verify_auth0_token, get_or_create_user_from_token
from django.contrib.auth import login as auth_login, logout as auth_logout


def login_view(request):
    """Redirect to Auth0 Universal Login."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    return _auth0_redirect(request, screen='login')


def signup_view(request):
    """Redirect to Auth0 signup screen."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    return _auth0_redirect(request, screen='signup')


def _auth0_redirect(request, screen='login'):
    state = secrets.token_urlsafe(32)
    request.session['auth0_state'] = state
    domain = getattr(settings, 'AUTH0_DOMAIN', '').strip()
    client_id = getattr(settings, 'AUTH0_APP_ID', '').strip()
    if not domain or not client_id:
        return render(request, 'accounts/login.html', {'auth0_configured': False})
    redirect_uri = request.build_absolute_uri('/accounts/callback/')
    auth_url = (
        f"https://{domain}/authorize"
        f"?response_type=code"
        f"&client_id={client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&scope=openid profile email"
        f"&state={state}"
    )
    if screen == 'signup':
        auth_url += "&screen_hint=signup"
    return redirect(auth_url)


def logout_view(request):
    auth_logout(request)
    return redirect('home')


def callback(request):
    """Handle Auth0 callback, exchange code for token, create/login user."""
    state = request.GET.get('state')
    code = request.GET.get('code')
    if not state or state != request.session.get('auth0_state'):
        return redirect('login')
    request.session.pop('auth0_state', None)
    if not code:
        return redirect('login')
    domain = getattr(settings, 'AUTH0_DOMAIN', '').strip()
    client_id = getattr(settings, 'AUTH0_APP_ID', '').strip()
    redirect_uri = request.build_absolute_uri('/accounts/callback/')
    token_url = f"https://{domain}/oauth/token"
    client_secret = getattr(settings, 'AUTH0_CLIENT_SECRET', '').strip()
    post_payload = {
        'grant_type': 'authorization_code',
        'client_id': client_id,
        'code': code,
        'redirect_uri': redirect_uri,
    }
    if client_secret:
        post_payload['client_secret'] = client_secret
    resp = http_requests.post(token_url, json=post_payload, headers={'Content-Type': 'application/json'}, timeout=10)
    if resp.status_code != 200:
        return redirect('login')
    data = resp.json()
    id_token = data.get('id_token')
    if not id_token:
        return redirect('login')
    token_payload = verify_auth0_token(id_token)
    if not token_payload:
        return redirect('login')
    user = get_or_create_user_from_token(token_payload)
    if user:
        auth_login(request, user, backend='django.contrib.auth.backends.ModelBackend')
    return redirect('dashboard')


from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.contrib import messages


@login_required
def profile_view(request):
    return render(request, 'accounts/profile.html')


@login_required
@require_http_methods(['GET', 'POST'])
def profile_edit(request):
    if request.method == 'POST':
        profile = getattr(request.user, 'profile', None)
        if profile:
            profile.display_name = request.POST.get('display_name', '')[:100]
            profile.phone = request.POST.get('phone', '')[:30]
            profile.save()
        request.user.first_name = request.POST.get('first_name', '')[:150]
        request.user.last_name = request.POST.get('last_name', '')[:150]
        request.user.email = request.POST.get('email', '')[:254]
        request.user.save()
        messages.success(request, 'Profile updated.')
        return redirect('profile')
    return render(request, 'accounts/profile_edit.html')


@login_required
def settings_view(request):
    return render(request, 'accounts/settings.html')


@login_required
def data_export(request):
    """GDPR data export."""
    import json
    from django.http import HttpResponse
    user = request.user
    data = {
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'username': user.username,
        'date_joined': user.date_joined.isoformat() if user.date_joined else None,
    }
    profile = getattr(user, 'profile', None)
    if profile:
        data['profile'] = {'role': profile.role, 'display_name': profile.display_name}
    response = HttpResponse(json.dumps(data, indent=2), content_type='application/json')
    response['Content-Disposition'] = 'attachment; filename="soulseer-data-export.json"'
    return response


@login_required
@require_http_methods(['GET', 'POST'])
def delete_account(request):
    if request.method == 'POST':
        user = request.user
        auth_logout(request)
        user.delete()
        return redirect('home')
    return render(request, 'accounts/delete_confirm.html')
