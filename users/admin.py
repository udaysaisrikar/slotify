from django.contrib import admin
from .models import Customer, ServiceProvider
# Register your models here.
@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('customer_id', 'first_name', 'last_name', 'email_id', 'phone_no')
    search_fields = ('first_name', 'last_name', 'email_id')
    list_filter = ('dob',)

@admin.register(ServiceProvider)
class ServiceProviderAdmin(admin.ModelAdmin):
    list_display = ('provider_id', 'business_name','name', 'email_id', 'phone_no', 'category_name')
    search_fields = ('business_name', 'name', 'email_id')
    list_filter = ('category_name',)
