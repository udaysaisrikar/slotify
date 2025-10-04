from django.contrib import admin
from .models import Appointments
# Register your models here.

@admin.register(Appointments)
class AppointmentsAdmin(admin.ModelAdmin):
    list_display = ('appointment_id', 'customer', 'provider', 'service', 'appointment_datetime', 'status', 'rating')
    search_fields = ('customer__first_name', 'provider__business_name', 'service__service_name')
    list_filter = ('status', 'appointment_datetime')

    