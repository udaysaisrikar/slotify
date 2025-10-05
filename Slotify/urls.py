"""
URL configuration for Slotify project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),

    # homepage
    path('', TemplateView.as_view(template_name="index.html"), name='home'),
    path('about/', TemplateView.as_view(template_name="about.html"), name='about'),
    path('contact/', TemplateView.as_view(template_name="contact_us.html"), name='contact'),
    path('privacy-policy/', TemplateView.as_view(template_name="privacy_policy.html"), name='privacy_policy'),
    path('terms-of-services/', TemplateView.as_view(template_name="terms_of_services.html"), name='terms_of_services'),

    # App URLs
    path('users/', include('users.urls')),
    path('services/', include('services.urls')),
    path('appointments/', include('appointments.urls')),
    # path('notifications/', include('notifications.urls')),
]
