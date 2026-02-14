"""
AI Engine admin configuration.
"""
from django.contrib import admin

from apps.ai_engine.models import AILog


@admin.register(AILog)
class AILogAdmin(admin.ModelAdmin):
    list_display = [
        'provider', 'model_name', 'task_type', 'success',
        'input_tokens', 'output_tokens', 'cost_usd', 'latency_ms',
        'created_at',
    ]
    list_filter = ['provider', 'task_type', 'success', 'created_at']
    search_fields = ['model_name', 'error_message']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'
