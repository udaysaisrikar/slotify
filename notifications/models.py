from django.db import models
from users.models import Customer, ServiceProvider
from appointments.models import Appointments

# Create your models here.

class Notifications(models.Model):
    notification_ID = models.BigAutoField(primary_key=True)
    recipient_customer = models.ForeignKey(Customer, on_delete=models.CASCADE, blank=True, null=True)
    recipient_provider = models.ForeignKey(ServiceProvider, on_delete=models.CASCADE, blank=True, null=True)
    appointment = models.ForeignKey(Appointments, on_delete=models.CASCADE, blank=True, null=True)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
