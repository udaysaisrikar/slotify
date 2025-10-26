from django.db import models
from django.contrib.auth.hashers import make_password, check_password
# Create your models here.
class Customer(models.Model):
    customer_id = models.BigAutoField(primary_key=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    dob = models.DateField(blank=True, null=True)
    email_id = models.EmailField(unique=True)
    phone_no = models.CharField(max_length=20, blank=True, null=True)
    password = models.CharField(max_length=255)

class ServiceProvider(models.Model):
    provider_id = models.CharField(max_length=255, primary_key=True)
    business_name = models.CharField(max_length=150)
    name = models.CharField(max_length=150, blank=True, null=True)
    email_id = models.EmailField(unique=True)
    phone_no = models.CharField(max_length=255)
    address = models.CharField(max_length=255, blank=True, null=True)
    category_name = models.CharField(max_length=255)
    password = models.CharField(max_length=255)
    category_id = models.ForeignKey('services.ServiceCategory', on_delete=models.SET_NULL, null=True)
    profile_views = models.PositiveIntegerField(default=0)
    experience = models.IntegerField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    title = models.CharField(max_length=255, null=True, blank=True)

    # Business hours fields
    start_hours = models.TimeField(null=True, blank=True)
    end_hours = models.TimeField(null=True, blank=True)
    