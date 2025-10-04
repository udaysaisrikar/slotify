from django.contrib import admin
from .models import ServiceCategory, Services, ProviderSchedule
# Register your models here.

@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ('category_id', 'category_name')
    search_fields = ('category_name',)

@admin.register(Services)
class ServicesAdmin(admin.ModelAdmin):
    list_display = ('service_id', 'service_name', 'category_id', 'provider_id', 'duration')
    search_fields = ('service_name',)
    list_filter = ('category_id', 'provider_id')

@admin.register(ProviderSchedule)
class ProviderScheduleAdmin(admin.ModelAdmin):
    list_display = ('schedule_id', 'service_id', 'day_of_week', 'available_time')
    list_filter = ('day_of_week', 'service_id')