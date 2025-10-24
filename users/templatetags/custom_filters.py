from django import template
from django.utils import timezone

register = template.Library()

@register.filter
def hours_since(value):
    """Return how long ago (in hours or days) something happened."""
    if not value:
        return ""
    now = timezone.now()
    diff = now - value
    total_seconds = diff.total_seconds()

    # Calculate hours and days
    hours = int(total_seconds // 3600)
    days = int(hours // 24)

    if hours < 1:
        return "Just now"
    elif hours < 24:
        return f"{hours} hour ago" if hours == 1 else f"{hours} hours ago"
    else:
        return f"{days} day ago" if days == 1 else f"{days} days ago"
