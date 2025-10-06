from django.shortcuts import render, get_object_or_404
from .models import Services, ServiceCategory

# Create your views here.

def category_view(request, category_name):
    # Fetch services matching the category
    category = get_object_or_404(ServiceCategory, category_name=category_name)

    # Fetch all services belonging to this category
    services = Services.objects.filter(category_id=category)
    context = {
        'category_name':category.category_name,
        'services':services,
    }

    return render(request, 'common_category_page.html', context)