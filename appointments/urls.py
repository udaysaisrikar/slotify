from django.urls import path
from . import views

urlpatterns = [
    path('appointments/', views.book_appointment_view, name='book_appointment'),
    path('reschedule/', views.reschedule_app, name='reschedule_app'),
]