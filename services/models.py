from django.db import models
from users.models import ServiceProvider
# Create your models here.
class ServiceCategory(models.Model):
    category_id = models.BigAutoField(primary_key=True)
    category_name = models.CharField(max_length=100, unique=True)


class Services(models.Model):
    service_id = models.BigAutoField(primary_key=True)
    service_name = models.CharField(max_length=150)
    description = models.CharField(max_length=255, blank=True, null=True)
    duration = models.CharField(max_length=50, blank=True, null=True)  # 2 hours
    category_id = models.ForeignKey(ServiceCategory, on_delete=models.SET_NULL, null=True)
    provider_id = models.ForeignKey(ServiceProvider, on_delete=models.CASCADE)


class ProviderSchedule(models.Model):
    schedule_id = models.BigAutoField(primary_key=True)
    service = models.ForeignKey(Services, on_delete=models.CASCADE)
    provider = models.ForeignKey(ServiceProvider, on_delete=models.CASCADE, null=True, blank=True)
    day_of_week = models.CharField(
        max_length=10,
        choices=[
            ('Monday','Monday'), ('Tuesday','Tuesday'), ('Wednesday','Wednesday'),
            ('Thursday','Thursday'), ('Friday','Friday'), ('Saturday','Saturday'), ('Sunday','Sunday')
        ]
    )
    available_time = models.CharField(max_length=20)
    booked_slots = models.JSONField(default=dict, blank=True) #JSON Object
    blocked_time = models.JSONField(default=list, blank=True)
