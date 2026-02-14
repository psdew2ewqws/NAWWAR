"""
Custom template tags and filters for the Nawwar dashboard.
"""
from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def format_fils(value):
    """
    Convert fils to JOD display string.

    Usage: {{ amount_fils|format_fils }}
    Output: "1.250 JOD" for 1250 fils
    """
    try:
        fils = int(value)
        jod = fils / 1000
        return f"{jod:,.3f} JOD"
    except (ValueError, TypeError):
        return value


@register.filter
def format_mw(value):
    """
    Format megawatt values with the MW suffix.

    Usage: {{ capacity|format_mw }}
    Output: "390 MW"
    """
    try:
        mw = int(value)
        return f"{mw:,} MW"
    except (ValueError, TypeError):
        return value


@register.simple_tag
def status_badge(status_value):
    """
    Render a coloured status badge for plant/unit status.

    Usage: {% status_badge "running" %}
    Output: <span class="badge badge-running">Running</span>
    """
    labels = {
        'running': ('Running', 'success'),
        'maintenance': ('Maintenance', 'warning'),
        'offline': ('Offline', 'danger'),
        'standby': ('Standby', 'secondary'),
    }
    label, css_class = labels.get(status_value, (status_value, 'secondary'))
    return mark_safe(
        f'<span class="badge bg-{escape(css_class)}">{escape(label)}</span>'
    )
