from django.shortcuts import render, get_object_or_404
from .models import Services, ServiceCategory

# Create your views here.

def category_view(request, category_id):
    # Fetch services matching the category
    category = ServiceCategory(pk=category_id)
    services = Services.objects.filter(category_id=category)
    context = {
        'category_name':category,
        'services':services,
    }

    return render(request, 'common_category_page.html', context)