from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from .models import ForumCategory, ForumThread, ForumPost


def forum_list(request):
    categories = ForumCategory.objects.prefetch_related('threads').order_by('order')
    return render(request, 'community/forum_list.html', {'categories': categories})


def thread_detail(request, pk):
    thread = get_object_or_404(ForumThread.objects.select_related('category', 'author').prefetch_related('posts__author'), pk=pk)
    return render(request, 'community/thread_detail.html', {'thread': thread})


@login_required
def create_thread(request, category_id):
    cat = get_object_or_404(ForumCategory, pk=category_id)
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        body = request.POST.get('body', '').strip()
        if title and body:
            thread = ForumThread.objects.create(category=cat, author=request.user, title=title)
            ForumPost.objects.create(thread=thread, author=request.user, body=body)
            return redirect('thread_detail', pk=thread.pk)
    return render(request, 'community/create_thread.html', {'category': cat})


@login_required
@require_POST
def reply(request, thread_id):
    thread = get_object_or_404(ForumThread, pk=thread_id)
    body = request.POST.get('body', '').strip()
    if body:
        ForumPost.objects.create(thread=thread, author=request.user, body=body)
    return redirect('thread_detail', pk=thread_id)
