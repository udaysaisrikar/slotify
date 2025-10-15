from django.db import models
from users.models import Customer, ServiceProvider
from services.models import Services
# Create your models here.

class Appointments(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Confirmed', 'Confirmed'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
    ]
    appointment_id = models.BigAutoField(primary_key=True)
    app_start_time = models.DateTimeField()
    app_end_time = models.DateTimeField(blank=True, null=True)
    cust_req = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Pending')

    # Review fields (filled only after completion)
    rating = models.IntegerField(null=True, blank=True)  # 1-5
    comments = models.TextField(blank=True, null=True)

    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True)
    provider = models.ForeignKey(ServiceProvider, on_delete=models.SET_NULL, null=True)
    service = models.ForeignKey(Services, on_delete=models.SET_NULL, null=True)


