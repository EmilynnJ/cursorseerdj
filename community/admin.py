from django.contrib import admin
from .models import ForumCategory, ForumThread, ForumPost, PostAttachment, Flag


@admin.register(ForumCategory)
class ForumCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'order')


@admin.register(ForumThread)
class ForumThreadAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'author', 'created_at')


@admin.register(ForumPost)
class ForumPostAdmin(admin.ModelAdmin):
    list_display = ('thread', 'author', 'created_at')


@admin.register(PostAttachment)
class PostAttachmentAdmin(admin.ModelAdmin):
    list_display = ('post',)


@admin.register(Flag)
class FlagAdmin(admin.ModelAdmin):
    list_display = ('content_type', 'object_id', 'reporter', 'status', 'reason')
    list_filter = ('status',)
