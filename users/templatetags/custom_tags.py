from django import template
register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Template filter to safely get dictionary items"""
    if isinstance(dictionary, dict):
        return dictionary.get(key, {})
    return {}

@register.filter
def get_items(dictionary, key):
    try:
        return dictionary.get(int(key))
    except (ValueError, TypeError):
        return dictionary.get(key)
    
@register.filter
def to(start, end):
    """"Usage: {% for i in 1|to:5 %}"""
    return range(start, end+1)

@register.filter
def star_type(value, avg_rating):
    """
    Returns 'full', 'half', or 'empty' depending on star position.
    """
    if value <= avg_rating:
        return "full"
    elif value - avg_rating < 1:
        return "half"
    return "empty"