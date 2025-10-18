from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json
from django.utils import timezone
from .models import Appointments
from users.models import Customer, ServiceProvider
from services.models import ProviderSchedule, Services
from datetime import datetime, timedelta

# Create your views here.
@csrf_exempt
@require_POST
def book_appointment_view(request):
    if request.method == "POST":
        data = json.loads(request.body)
        # Get customer
        customer_id = request.session.get('customer_id')
        customer = Customer.objects.get(customer_id=customer_id)

        provider_id = request.session.get("selected_provider_id")
        selected_date = data.get("appointment_date")

        selected_date_obj = datetime.strptime(selected_date, "%Y-%m-%d").date()
        day_of_week = selected_date_obj.strftime("%A")

        service_id = data.get("service_id")
        selected_time = data.get("selected_time")
        print("time:", selected_time)
        notes = data.get("notes")

        if not (selected_date and service_id and selected_time):
            return JsonResponse({"success": False, "error": "Missing required details"})

        try:
            provider = get_object_or_404(ServiceProvider, provider_id=provider_id)
            service = Services.objects.get(service_id=service_id)

            # ---- Calculate start and end times ----
            start_str = f"{selected_date} {selected_time}"  # "2025-10-16 14:00"
            naive_start = datetime.strptime(start_str, "%Y-%m-%d %H:%M")
            app_start_time = timezone.make_aware(naive_start)
            app_end_time = app_start_time + timedelta(minutes=int(service.duration))

            # ---- Create Appointment ----
            Appointments.objects.create(
                app_start_time = app_start_time,
                app_end_time = app_end_time,
                cust_req = notes or "",
                status = "Pending",
                customer = customer,
                provider = provider,
                service = service
            )

            # Update Provider Schedule
            schedule, created = ProviderSchedule.objects.get_or_create(
                provider = provider,
                service = service, 
                day_of_week = day_of_week
            )

            # Store Booked Slot
            booked_slots = schedule.booked_slots or {}
            booked_slots[str(selected_date)] = booked_slots.get(str(selected_date), [])
            booked_slots[str(selected_date)].append({
                "start":selected_time,
                "end":app_end_time.strftime("%H:%M")
            })
            schedule.booked_slots = booked_slots
            schedule.save()

            return JsonResponse({"success": True, "message": "Appointment Booked Successfully!"})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})

    return JsonResponse({"success": False, "error": "Invalid request"})