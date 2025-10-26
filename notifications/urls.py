from django.urls import path
from . import views

urlpatterns = [
    path('notifications/mark_all_as_read/', views.mark_all_as_read, name='mark_all_as_read'),
]