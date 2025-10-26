from django.db import models
from users.models import Customer, ServiceProvider
from appointments.models import Appointments

# Create your models here.

class Notifications(models.Model):
    user = models.ForeignKey(Customer, on_delete=models.CASCADE, null=True, blank=True)
    provider = models.ForeignKey(ServiceProvider, on_delete=models.CASCADE, null=True, blank=True)
    title = models.CharField(max_length=255, default="Untitled")
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
