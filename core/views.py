from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required


def home(request):
    return render(request, 'core/home.html')


def about(request):
    return render(request, 'core/about.html')


def help_center(request):
    return render(request, 'core/help_center.html')


def privacy(request):
    return render(request, 'core/privacy.html')


def terms(request):
    return render(request, 'core/terms.html')


@login_required
def dashboard(request):
    profile = getattr(request.user, 'profile', None)
    if profile and profile.is_reader:
        return redirect('reader_dashboard')
    if profile and profile.is_admin:
        return redirect('admin_dashboard')
    return redirect('client_dashboard')
