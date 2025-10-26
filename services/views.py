from django.shortcuts import render, get_object_or_404, redirect
from .models import Services, ServiceCategory, ProviderSchedule
from users.models import ServiceProvider
from django.contrib.auth.decorators import login_required
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


# def filter_providers(request):
#     category = request.POST.get("category")
#     selected_date = request.POST.get("date")
#     time_slot = request.POST.get("time")
