from django.urls import path
from . import views

urlpatterns = [
    # Customer
    path('cus_signup/', views.customer_signup, name='cus_signup'),
    path('cus_signin/', views.customer_signin, name='cus_signin'),
    path('cus_logout/', views.customer_logout, name='cus_logout'),
    path('customer-dashboard/', views.customer_dashboard, name='customer_dashboard'),

    # Service Provider
    path('sp_signup/', views.provider_signup, name='sp_signup'),
    path('sp_signin/', views.provider_signin, name='sp_signin'),
    path('sp_logout/', views.provider_logout, name='sp_logout'),
    path('provider-dashboard/', views.provider_dashboard, name='provider_dashboard'),
]