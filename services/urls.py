from django.urls import path
from . import views

urlpatterns = [
    path('<str:category_name>/', views.category_view, name='category_page'),
    path('filter-providers/', views.filter_providers, name='filter_providers'),
]