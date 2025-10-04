from django.contrib import admin
from .models import Notifications
# Register your models here.

@admin.register(Notifications)
class NotificationsAdmin(admin.ModelAdmin):
    list_display = ('notification_ID', 'recipient_customer', 'recipient_provider', 'appointment', 'is_read', 'created_at')
    search_fields = ('recipient_customer__first_name', 'recipient_provider__business_name')
    list_filter = ('is_read', 'created_at')