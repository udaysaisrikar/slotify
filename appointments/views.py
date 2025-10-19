from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json
from django.utils import timezone
from .models import Appointments
from users.models import Customer, ServiceProvider
from services.models import ProviderSchedule, Services
from datetime import datetime, timedelta
from django.contrib import messages
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


def reschedule_app(request):
    if request.method == "POST":
        app_id = request.POST.get("appointment_id")
        new_date = request.POST.get("reschedule_date")
        new_time = request.POST.get("reschedule_time")

        # Get Appointment
        appointment = get_object_or_404(Appointments, appointment_id = app_id)
        service = appointment.service
        provider = appointment.provider

        # Find schedule for selected date and provider
        selected_day = datetime.strptime(new_date, "%Y-%m-%d").strftime("%A")
        schedule = ProviderSchedule.objects.filter(
            provider=provider,
            service=service,
            day_of_week=selected_day
        ).first()

        if not schedule:
            messages.error(request, "No Schedule available for this date.")
            return redirect('customer_dashboard')

        # Convert times
        selected_date = new_date
        selected_time = datetime.strptime(new_time, "%H:%M")
        new_start = datetime.combine(datetime.strptime(selected_date, "%Y-%m-%d").date(), selected_time.time())
        new_end = new_start + timedelta(minutes=int(service.duration))

        # ---- Check Blocked Times ----
        blocked_for_date = [b for b in schedule.blocked_time if b.get("date") == selected_date]
        for b in blocked_for_date:
            blocked_start = datetime.strptime(b["start"], "%H:%M")
            if selected_time == blocked_start:
                messages.error(request, "This time is blocked by the provider.")
                return redirect('customer_dashboard')
            
        # ---- Check Booked Slots ----
        booked_for_date = schedule.booked_slots.get(selected_date, [])
        for booked in booked_for_date:
            booked_start = datetime.strptime(booked["start"], "%H:%M")
            booked_end = datetime.strptime(booked["end"], "%H:%M")
            # Overlap Check
            if not (new_end <= booked_start or new_start >= booked_end):
                messages.error(request, "This slot is already booked by another customer.")
                return redirect("customer_dashboard")
            
        # Remove old Booked Slot
        old_date_str = appointment.app_start_time.date().isoformat()
        if schedule.booked_slots.get(old_date_str):
            old_list = schedule.booked_slots[old_date_str]
            update_list = [
                b for b in old_list
                if not (
                    b["start"] == appointment.app_start_time.strftime("%H:%M") and
                    b["end"] == appointment.app_end_time.strftime("%H:%M")
                )
            ]
            if update_list:
                schedule.booked_slots[old_date_str] = update_list
            else:
                schedule.booked_slots.pop(old_date_str, None)

        # Add new Booking Slot
        date_str = selected_date
        booked_for_date = schedule.booked_slots.get(date_str, [])
        booked_for_date.append({
            "start": new_start.strftime("%H:%M"),
            "end": new_end.strftime("%H:%M")
        })
        schedule.booked_slots[date_str] = booked_for_date
        schedule.save()

        # Update Appointment
        appointment.app_start_time = new_start
        appointment.app_end_time = new_end
        appointment.save()

        messages.success(request, "Appointment rescheduled successfully.")
        return redirect('customer_dashboard')
    
    return redirect('customer_dashboard')