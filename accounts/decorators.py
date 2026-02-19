from functools import wraps
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required


def require_role(*roles):
    """Decorator: require user to have one of the given roles."""
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped(request, *args, **kwargs):
            profile = getattr(request.user, 'profile', None)
            if not profile or profile.role not in roles:
                return redirect('dashboard')
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator
