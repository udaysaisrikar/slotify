from django.shortcuts import render, get_object_or_404, redirect
from .models import Services, ServiceCategory, ProviderSchedule
from users.models import ServiceProvider
from appointments.models import Appointments
from django.http import JsonResponse
from django.db.models import Avg, Count
from django.contrib.auth.decorators import login_required
from datetime import datetime, date, timedelta
# Create your views here.

def category_view(request, category_name):
    # Fetch services matching the category
    category = get_object_or_404(ServiceCategory, category_name=category_name)

    # Fetch all services belonging to this category
    services = Services.objects.filter(category_id=category)
    providers = ServiceProvider.objects.all()
    providers = providers.filter(category_name=category.category_name)
    total_reviews = 0
    for provider in providers:
        avg_rating = Appointments.objects.filter(
        provider=provider, status='completed', rating__isnull=False
        ).aggregate(avg=Avg('rating'))['avg'] or 0
        avg_rating = round(avg_rating, 1)
        provider.rating = avg_rating

        reviews = Appointments.objects.filter(
            provider=provider,
            rating__isnull=False
        ).order_by('-app_start_time')
        total_reviews += reviews.count()
        provider.total_reviews = total_reviews

    context = {
        'category_name':category.category_name,
        'services':services,
        'providers':providers
    }
    print(providers)

    return render(request, 'common_category_page.html', context)


def filter_providers(request):
    category = request.POST.get("category")
    selected_date = request.POST.get("date")
    time_slot = request.POST.get("time")
    rating_filter = request.POST.getlist("rating")
    availability = request.POST.getlist("availability")

    providers = ServiceProvider.objects.all()

    if category:
        providers = providers.filter(category_name__icontains=category)
    context = {
        "providers":providers,
    }
    return render(request, "common_category_page.html", context)