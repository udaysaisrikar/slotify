from django.shortcuts import render

# Create your views here.

def customer_dashboard(request):
    return render(request, 'customer_dashboard.html')

def provider_dashboard(request):
    return render(request, 'provider_dashboard.html')
