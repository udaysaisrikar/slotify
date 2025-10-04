from django.db import models

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

    