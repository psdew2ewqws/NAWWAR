from django.contrib import admin

from .models import Post


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ['seq_id', 'title', 'author', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['title', 'content', 'seq_id']
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ['seq_id', 'created_at', 'updated_at']
    ordering = ['-created_at']
