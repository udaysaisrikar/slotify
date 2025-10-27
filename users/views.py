from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.hashers import make_password, check_password
from .models import Customer, ServiceProvider
from services.models import ServiceCategory, Services
from django.core.mail import send_mail
from django.db import transaction
from services.models import ProviderSchedule
from datetime import datetime, timedelta, date
from appointments.models import Appointments
import json
from django.utils import timezone
from django.http import JsonResponse
from django.db.models import Avg, Count, Q
from collections import Counter
from notifications.models import Notifications
# Create your views here.


def to_time(t):
    return datetime.strptime(t, "%H:%M").time()


def set_selected_provider(request):
    if request.method == "POST":
        data = json.loads(request.body)
        provider_id = data.get("provider_id")

        request.session["selected_provider_id"] = provider_id
        return JsonResponse({"message":"Provider stored in session"})
    return JsonResponse({"error":"Invalid request"}, status=400)


def set_selected_date(request):
    if request.method == "POST":
        data = json.loads(request.body)
        selected_date = data.get("appointment_date")
        request.session["selected_date"] = selected_date
        request.session.modified = True
        return JsonResponse({"message":"Date stored in session"})
    return JsonResponse({"error":"Invalid request"}, status=400)


# Customer Dashboard
def customer_dashboard(request):
    if 'customer_id' not in request.session:
        return redirect('home')
    
    customer_id = request.session.get('customer_id')
    customer = Customer.objects.get(customer_id = customer_id)
    
    providers = ServiceProvider.objects.all()

    # ----------------------
    # Handle Cancellation
    # ----------------------
    if request.method == "POST" and "cancel_app" in request.POST:
        appointment_id = request.POST.get("cancel_app")
        try:
            appointment = Appointments.objects.get(appointment_id=appointment_id, customer__customer_id=customer_id)
            appointment.status = "Cancelled"
            appointment.save()

            # Update Booked slots
            day_of_week = appointment.app_start_time.strftime("%A")
            schedule = ProviderSchedule.objects.filter(provider=appointment.provider, service=appointment.service, day_of_week=day_of_week).first()
            print(schedule)
            if schedule:
                booked_slots = schedule.booked_slots or {}
                print("Book", booked_slots)
                date_str = appointment.app_start_time.date().isoformat()
                print("Date", date_str)
                booked_for_date = schedule.booked_slots.get(date_str, [])
                
                booked_for_date = [
                    b for b in booked_for_date
                    if b["start"] != appointment.app_start_time.strftime("%H:%M") or 
                        b["end"] != appointment.app_end_time.strftime("%H:%M")
                ]
                print("book", booked_for_date)
                if booked_for_date:
                    schedule.booked_slots[date_str] = booked_for_date
                else:
                    schedule.booked_slots.pop(date_str, None)

                schedule.save()
            # ✅ Create notification for Customer
            Notifications.objects.create(
                user=appointment.customer,
                provider=appointment.provider,
                title="Appointment Cancelled",
                message=f"Your appointment for '{appointment.service.service_name}' was cancelled by {appointment.customer.first_name}.",
                created_at=timezone.now()
            )
            messages.success(request, "Appointment Cancelled Successfully!")
        except Appointments.DoesNotExist:
            pass
        return redirect('customer_dashboard')

    # Searching providers
    if request.method == "POST":
        customer_id = request.session.get('customer_id')
        customer = Customer.objects.get(pk=customer_id)
        category = request.POST.get('category')
        date = request.POST.get('date')
        query = request.POST.get('query')

        providers = ServiceProvider.objects.all()

        if category:
            providers = providers.filter(category_name__icontains=category)
        if query:
            providers = providers.filter(business_name__icontains=query)
        if date:
            pass
    providers = ServiceProvider.objects.annotate(avg_rating_now=Avg('appointments__rating'))

    # Fetching Services of Selected Provider to Book Appointment
    services = None
    time_slots = []
    selected_date = None
    selected_provider = None
    provider_id = request.session.get("selected_provider_id")
    
    print("PID:", provider_id)
    if provider_id:
        selected_provider = get_object_or_404(ServiceProvider, provider_id=provider_id)
        services = Services.objects.filter(provider_id=selected_provider)

        # ----- Displaying time slots -----
        selected_date = datetime.today().strftime("%Y-%m-%d")
        print("View:",selected_date)
        time_slots = []
        if selected_date:
            # find schedule by weekday
            weekday = datetime.today().strftime("%A")
            schedule = ProviderSchedule.objects.filter(provider=selected_provider, day_of_week=weekday).first()
            if schedule and schedule.available_time:
                try:
                    start_str, end_str = schedule.available_time.split("-")
                    start = datetime.strptime(start_str, "%H:%M")
                    end = datetime.strptime(end_str, "%H:%M")
                    # Build all hourly slots
                    while start < end:
                        slot_time = start.strftime("%H:%M")
                        time_slots.append(slot_time)
                        start += timedelta(hours=1)
                    
                    # Get blocked or booked
                    blocked_times = [b for b in schedule.blocked_time if b["date"] == selected_date]
                    booked_for_date = schedule.booked_slots.get(selected_date, [])
                    # Mark each slot
                    for i, slot in enumerate(time_slots):
                        is_blocked = any(b["start"] == slot for b in blocked_times)
                        is_booked = slot in booked_for_date
                        time_slots[i] = {
                            "time":slot,
                            "available":not (is_blocked or is_booked)
                        }
                except Exception as e:
                    print("Error:",e)
        

    # -----------------------
    # Fetching all Appointments of Customer
    # -----------------------
    now = timezone.now()
    Appointments.objects.filter(
        customer__customer_id = customer_id, 
        app_end_time__lt=now
        ).exclude(status__in=["Completed", "Cancelled"]).update(status="Completed")
    
    # Categorize by Status
    upcoming = Appointments.objects.filter(customer=customer, status__in=["Pending", "Confirmed"]).order_by('app_start_time')
    completed = Appointments.objects.filter(customer=customer, status='Completed').order_by('-app_start_time')
    cancelled = Appointments.objects.filter(customer=customer, status='Cancelled').order_by('-app_start_time')

    
    total_appointments = upcoming.count() + completed.count() + cancelled.count()
    attendence_rate = 0
    if total_appointments > 0:
        attendence_rate = int((completed.count() / total_appointments) * 100)

    recent_appointments = Appointments.objects.filter(customer=customer).exclude(status__in=["Cancelled","Completed"]).order_by('-app_start_time')[:3]
    
    notifications = Notifications.objects.filter(user=customer).order_by('-created_at')
    notification_length = Notifications.objects.filter(user=customer, is_read=False).order_by('-created_at')
    context = {
        'providers':providers,
        'customer':customer,
        'services':services,
        'time_slots':time_slots,
        'selected_date':selected_date,
        'selected_provider':selected_provider,
        'upcoming':upcoming,
        'completed':completed,
        'cancelled':cancelled,
        'attendence_rate':attendence_rate,
        'recent_appointments':recent_appointments,
        'notifications':notifications,
        'notification_len':notification_length
    }

    return render(request, 'customer_dashboard.html', context)



# Customer Sign Up
def customer_signup(request):
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        dob = request.POST.get('dob')
        email = request.POST.get('email_id')
        phone = request.POST.get('phone_no')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        if password != confirm_password:
            messages.error(request, "Password do not match!")
            return redirect('home')
        
        if Customer.objects.filter(email_id=email).exists():
            messages.error(request, "Email already exists!")
            return redirect('home')
        
        Customer.objects.create(
            first_name = first_name,
            last_name = last_name,
            dob = dob,
            email_id = email,
            phone_no = phone,
            password = make_password(password) # Encrypt password
        )

        messages.success(request, "Account created Successsfully! Please log in.")
        return redirect('home')
    
    return redirect('home')


# Customer Sign In
def customer_signin(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        try:
            customer = Customer.objects.get(email_id=email)
        except Customer.DoesNotExist:
            messages.error(request, "No account found with this email!! Try to create account.")
            return redirect('home')
        
        if check_password(password, customer.password):
            request.session['customer_id'] = customer.customer_id
            request.session['customer_fname'] = customer.first_name
            request.session['customer_lname'] = customer.last_name
            request.session['user_type'] = 'customer'
            # messages.success(request, f"Welcome, {customer.first_name}!")
            return redirect('customer_dashboard')
        else:
            messages.error(request, "Incorrect password.")
            return redirect('home')
        
    return redirect('home')


# Customer LogOut
def customer_logout(request):
    request.session.flush()
    messages.info(request, "Logged out successfully.")
    return redirect('home')



# To generate SP ID
def generate_provider_id():
    from .models import ServiceProvider
    last_provider = ServiceProvider.objects.order_by('-provider_id').first()
    if last_provider:
        last_id = int(last_provider.provider_id.replace("SP", ""))
        new_id = f"SP{last_id + 1:03d}"
    else:
        new_id = "SP001"

    return new_id




# Provider Sign Up
def provider_signup(request):
    if request.method == 'POST':
        business_name = request.POST.get('business_name')
        name = request.POST.get('name')
        email = request.POST.get('email_id')
        phone = request.POST.get('phone_no')
        address = request.POST.get('address')
        category_name = request.POST.get('service_category')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        start_hours = request.POST.get('start_hours')
        end_hours = request.POST.get('end_hours')

        # Check if passwords match or not
        if password != confirm_password:
            messages.error(request, "Password do not match!")
            return redirect('home')
        
        # Check if email already exists
        if ServiceProvider.objects.filter(email_id = email).exists():
            messages.error(request, "Email already registered!")
            return redirect('home')
        
        # Generate new Provider ID
        provider_id = generate_provider_id()

        # Get category details
        category = ServiceCategory.objects.get(category_name = category_name)        

        # send Provider ID via Email
        subject = "Welcome to Slotify! Your Provider ID"
        message = (
            f"Hello {name or business_name},\n\n"
            f"Your account has been successfully created.\n\n"
            f"Your Service Provider ID is: {provider_id}\n\n"
            "You can now log in to your Slotify Provider Dashboard.\n\n"
            "Thank you,\nSlotify Team"
        ) 

        try:
            send_mail(subject, message, 'slotify.notifications@gmail.com', [email], fail_silently=False)
            messages.success(request, "SignUp Successful! Check you email for your Provider ID.")
        except Exception as e:
            messages.warning(request, f"Signup successful, but failed to send email: {e}")
            return redirect('home')
        
        with transaction.atomic():
            # Create the Provider
            service_provider = ServiceProvider.objects.create(
            provider_id = provider_id,
            business_name = business_name,
            name = name,
            email_id = email,
            phone_no = phone,
            address = address,
            category_name = category_name,
            password = make_password(password),
            category_id = category,
            start_hours=start_hours,
            end_hours=end_hours
        )
    
    return redirect('home')


# Provider SignIn
def provider_signin(request):
    if request.method == 'POST':
        provider_id = request.POST.get('provider_id')
        email = request.POST.get('email_id')
        password = request.POST.get('password')

        try:
            provider = ServiceProvider.objects.get(provider_id=provider_id, email_id=email)
        except ServiceProvider.DoesNotExist:
            messages.error(request, "No account found with this email and ID!! Try to create account.")
            return redirect('home')            
        
        # Check Password
        if check_password(password, provider.password):
            request.session['provider_id'] = provider.provider_id
            request.session['user_type'] = 'provider'
            return redirect('provider_dashboard')
        else:
            messages.error(request, "Passwords do not match.")
            return redirect('home')
        
    return redirect('home')    
    

# Provider LogOut
def provider_logout(request):
    request.session.flush()
    messages.info(request, "Logged out successfully.")
    return redirect('home')
        


# Update profiles
def update_profile(request):
    user_type = request.session.get('user_type') # Customer or Provider
    cus_id = request.session.get('customer_id')
    sp_id = request.session.get('provider_id')

    if request.method == 'POST':
        if user_type == 'customer':
            customer = Customer.objects.get(customer_id=cus_id)
            first_name = request.POST.get('first_name') or customer.first_name
            last_name = request.POST.get('last_name') or customer.last_name
            email_id = request.POST.get('email_id') or customer.email_id
            phone_no = request.POST.get('phone_no') or customer.phone_no
            dob = request.POST.get('dob') or customer.dob
            # Update Customer
            customer.first_name = first_name
            customer.last_name = last_name
            customer.email_id = email_id
            customer.phone_no = phone_no
            if dob:
                customer.dob = dob
            customer.save()
            messages.success(request, "Profile updated successfully!")

        elif user_type == 'provider':
            provider = ServiceProvider.objects.get(provider_id=sp_id)
            name = request.POST.get('name') or provider.name
            email_id = request.POST.get('email') or provider.email_id
            phone_no = request.POST.get('phone_no') or provider.phone_no
            address = request.POST.get('address') or provider.address
            experience = request.POST.get('experience') or provider.experience
            title = request.POST.get('title') or provider.title
            description = request.POST.get('description') or provider.description
            # Update Provider
            provider.name = name
            provider.email_id = email_id
            provider.phone_no = phone_no
            provider.address = address
            provider.experience = experience
            provider.title = title
            provider.description = description
            provider.save()
            messages.success(request, "Your profile updated successfully!")

        return redirect(f'{user_type}_dashboard')
    
    return redirect(f'{user_type}_dashboard')


# Delete account
def delete_account(request):
    user = request.session.get('user_type')
    if request.method == 'POST':
        # If user is Customer
        if 'customer_id' in request.session:
            customer = Customer.objects.get(pk=request.session['customer_id'])
            customer.delete()
            request.session.flush() # Clear the session
            messages.success(request, "Account deleted Successfully!")
            return redirect('home')
        
        # If user is Provider
        elif 'provider_id' in request.session:
            provider = ServiceProvider.objects.get(pk=request.session['provider_id'])
            provider.delete()
            request.session.flush()
            messages.success(request, "Account deleted Successfully!")
            return redirect('home')
        
    return redirect(f'{user}_dashboard')




# Provider Dashboard
DAYS_OF_WEEK = ["Monday","Tuesday", "Wednesday","Thursday","Friday","Saturday","Sunday"]
def provider_dashboard(request):
    provider_id = request.session.get('provider_id')
    if not provider_id:
        return redirect('home')
    
    provider = ServiceProvider.objects.get(provider_id=provider_id)
    category = provider.category_id

    # ----------------
    # Handle Add Service form submission
    # ----------------
    if request.method == 'POST' and 'service_name' in request.POST:
        service_name = request.POST.get('service_name')
        description = request.POST.get('description','')
        duration = request.POST.get('duration','')

        if service_name:
            Services.objects.create(
                service_name=service_name,
                description=description,
                duration=duration,
                category_id=category,
                provider_id=provider,
            )
            messages.success(request, "Service added Successfully!")
        return redirect('provider_dashboard')
    


    # ---------------
    # Handle Edit Service
    # ---------------
    if request.method == "POST" and request.POST.get("action") == "edit_service":
        provider_id = request.session.get('provider_id')
        provider = ServiceProvider(provider_id=provider_id)

        service_id = request.POST.get("service_id")
        name = request.POST.get("name")
        description = request.POST.get("description")
        duration = request.POST.get("duration")

        try:
            service = Services.objects.get(service_id=service_id, provider_id=provider)
            service.service_name = name
            service.description = description
            service.duration = duration
            service.save()
            messages.success(request, "Service Updated Successfully!")
        except Services.DoesNotExist:
            messages.error(request, "Service Not Found!")

        return redirect('provider_dashboard')
    


    # ----------------
    # Handle Delete Service
    # ----------------
    if request.method == "POST" and request.POST.get("action") == "delete_service":
        provider_id = request.session.get('provider_id')
        provider = ServiceProvider.objects.get(provider_id=provider_id)

        service_id = request.POST.get("service_id")
        try:
            service = Services.objects.get(service_id=service_id, provider_id=provider)
            service.delete()
            messages.success(request, "Service deleted Successfully!")
        except Services.DoesNotExist:
            messages.error(request, "Service not found!")
        
        return redirect('provider_dashboard')
    
    
    
    # Fetch all services added by this provider
    all_services = Services.objects.filter(provider_id=provider)
    categories = ServiceCategory.objects.all()

    

    # ----------------
    # Handle Weekly Schedule
    # ----------------
    if request.method == "POST" and 'schedule_submit' in request.POST:
        for day in DAYS_OF_WEEK:
            active = request.POST.get(f'{day}_active')
            start_time = request.POST.get(f'{day}_start')
            end_time = request.POST.get(f'{day}_end')

            if active:
                available_time = f"{start_time}-{end_time}"
                for service in all_services:
                    schedule, created = ProviderSchedule.objects.get_or_create(
                        provider = provider,
                        service=service,
                        day_of_week=day,
                        defaults={"available_time":available_time}
                    )

                    if not created:
                        schedule.available_time = available_time
                        schedule.save()
            else:
                for service in all_services:
                    try:
                        schedule = ProviderSchedule.objects.get(provider=provider, service=service, day_of_week=day)
                        schedule.available_time = ""
                        schedule.save()
                    except ProviderSchedule.DoesNotExist:
                        pass
        messages.success(request, "Your weekly schedule is updated successfully")
        return redirect('provider_dashboard')
    

    # -------------
    # Handle Blocking time
    # -------------
    if request.method == "POST" and "block_time_submit" in request.POST:
        provider_id = request.session.get('provider_id')
        provider = ServiceProvider.objects.get(provider_id=provider_id)

        day = request.POST.get("block_day")
        date = request.POST.get("block_date", "")
        start_time = request.POST.get("block_start")

        if not (day and start_time):
            messages.error(request, "Incomplete block time data.")
            return redirect('provider_dashboard')

        # Apply block to all services of this provider
        services = Services.objects.filter(provider_id=provider_id)
        success = False
        for service in services:
            schedule, created = ProviderSchedule.objects.get_or_create(
                provider=provider,
                service=service,
                day_of_week=day,
            )
            # Validate block time lies within available time (if available)
            if schedule.available_time:
                avail_start_str, avail_end_str = schedule.available_time.split('-')
                avail_start = to_time(avail_start_str)
                avail_end = to_time(avail_end_str)
                block_start = to_time(start_time)
                if not (avail_start <= block_start < avail_end):
                    messages.error(
                        request,
                        f"Blocked time ({block_start}) must be within your available hours ({avail_start}-{avail_end}) for {day}."
                    )   
                    break  # skip saving for this service    
                # return redirect('provider_dashboard')

            blocked_list = schedule.blocked_time or []
            already_exists = any(
                b["date"] == date and b["start"] == start_time
                for b in blocked_list
            )

            if already_exists:
                messages.warning(request, f"Time {start_time} on {day} is already blocked.")
                break  # skip adding duplicate

            blocked_list.append({
                "date":date,
                "start":start_time,
            })
            
            schedule.blocked_time = blocked_list
            schedule.save()
            success = True
        if success:
            messages.success(request, f"Time blocked successfully for {day}")
        return redirect('provider_dashboard')


    # Fetching Services of Selected Provider to Book Appointment
    services_book = None
    time_slots = []
    selected_date = None
    selected_provider = None
    provider_id = request.session.get("provider_id")
    
    print("PID:", provider_id)
    if provider_id:
        selected_provider = get_object_or_404(ServiceProvider, provider_id=provider_id)
        services_book = Services.objects.filter(provider_id=selected_provider)

        # ----- Displaying time slots -----
        selected_date = datetime.today().strftime("%Y-%m-%d")
        print("View:",selected_date)
        time_slots = []
        if selected_date:
            # find schedule by weekday
            weekday = datetime.today().strftime("%A")
            schedule = ProviderSchedule.objects.filter(provider=selected_provider, day_of_week=weekday).first()
            if schedule and schedule.available_time:
                try:
                    start_str, end_str = schedule.available_time.split("-")
                    start = datetime.strptime(start_str, "%H:%M")
                    end = datetime.strptime(end_str, "%H:%M")
                    # Build all hourly slots
                    while start < end:
                        slot_time = start.strftime("%H:%M")
                        time_slots.append(slot_time)
                        start += timedelta(hours=1)
                    
                    # Get blocked or booked
                    blocked_times = [b for b in schedule.blocked_time if b["date"] == selected_date]
                    booked_for_date = schedule.booked_slots.get(selected_date, [])
                    # Mark each slot
                    for i, slot in enumerate(time_slots):
                        is_blocked = any(b["start"] == slot for b in blocked_times)
                        is_booked = slot in booked_for_date
                        time_slots[i] = {
                            "time":slot,
                            "available":not (is_blocked or is_booked)
                        }
                except Exception as e:
                    print("Error:",e)

    # ----------------------
    # Handle Cancellation
    # ----------------------
    if request.method == "POST" and "cancel_app" in request.POST:
        appointment_id = request.POST.get("cancel_app")

        try:
            appointment = Appointments.objects.get(appointment_id=appointment_id)
            appointment.status = "Cancelled"
            appointment.save() 
            
            # Update Booked slots
            day_of_week = appointment.app_start_time.strftime("%A")
            schedule = ProviderSchedule.objects.filter(provider=appointment.provider, service=appointment.service, day_of_week=day_of_week).first()
            print(schedule)
            if schedule:
                booked_slots = schedule.booked_slots or {}
                print("Book", booked_slots)
                date_str = appointment.app_start_time.date().isoformat()
                print("Date", date_str)
                booked_for_date = schedule.booked_slots.get(date_str, [])
                
                booked_for_date = [
                    b for b in booked_for_date
                    if b["start"] != appointment.app_start_time.strftime("%H:%M") or 
                        b["end"] != appointment.app_end_time.strftime("%H:%M")
                ]
                print("book", booked_for_date)
                if booked_for_date:
                    schedule.booked_slots[date_str] = booked_for_date
                else:
                    schedule.booked_slots.pop(date_str, None)

                schedule.save()
            
            # ✅ Send cancellation email
            subject = "Your Appointment Has Been Cancelled"
            message = (
                f"Hi {appointment.customer.first_name},\n\n"
                f"Your appointment for '{appointment.service.service_name}' with "
                f"{appointment.provider.name} on "
                f"{appointment.app_start_time.strftime('%d %b %Y, %I:%M %p')} has been cancelled.\n\n"
                f"Please book another slot if needed.\n\n- Slotify Team"
            )
            send_mail(subject, message, 'slotify.notifications@gmail.com', [appointment.customer.email_id], fail_silently=False)

            # ✅ Create notification for Customer
            Notifications.objects.create(
                user=appointment.customer,
                provider=appointment.provider,
                title="Appointment Cancelled",
                message=f"Your appointment for '{appointment.service.service_name}' was cancelled by {appointment.provider.name}.",
                created_at=timezone.now()
            )
            messages.success(request, "Appointment Cancelled Successfully!")
        except Appointments.DoesNotExist:
            pass
        return redirect('provider_dashboard')

    # ----------------
    # Storing into schedule_dict
    # ----------------
    schedules = ProviderSchedule.objects.filter(provider=provider)
    schedule_dict = {day :{"available_time":"", "start_time": "09:00", "end_time": "17:00", "active": False} for day in DAYS_OF_WEEK}
    for s in schedules:
        start, end = "09:00", "17:00"
        if s.available_time:
            active = True
            try:
                start, end = s.available_time.split("-")
            except ValueError:
                start, end = "09:00", "17:00"
            schedule_dict[s.day_of_week] = {
                "available_time": s.available_time,
                "start_time":start,
                "end_time":end,
                "blocked_time": s.blocked_time,
                "booked_slots": s.booked_slots,
                "active":True,
            }
        else:
            schedule_dict[s.day_of_week] = {
                "available_time": "",
                "start_time":start,
                "end_time":end,
                "blocked_time": [],
                "booked_slots": s.booked_slots,
                "active":False,
            }


    # Get Customers Who has Appointments
    all_customers = Customer.objects.filter(appointments__provider=provider).distinct()
    for customer in all_customers:
        last_appointment = Appointments.objects.filter(provider=provider, customer=customer).order_by('-app_end_time').first()
        customer.last_visit = last_appointment.app_end_time.strftime("%d %b %Y") if last_appointment else None
        customer.total_visits = Appointments.objects.filter(provider=provider, customer=customer).count()

    # Accept Appointment
    if request.method == "POST":
        app_id = request.POST.get("appointment_id")
        appointment = Appointments.objects.get(appointment_id=app_id)
        if "accept_appointment" in request.POST:
                Appointments.objects.filter(appointment_id=app_id).update(status="Confirmed")
                # ✅ Send confirmation email
                subject = "Your Appointment Has Been Confirmed!"
                message = (
                    f"Hi {appointment.customer.first_name},\n\n"
                    f"Your appointment for '{appointment.service.service_name}' with "
                    f"{appointment.provider.name} has been confirmed.\n\n"
                    f"Date & Time: {appointment.app_start_time.strftime('%d %b %Y, %I:%M %p')}\n"
                    f"Thank you for choosing Slotify!\n\n- Slotify Team"
                )
                send_mail(subject, message, 'slotify.notifications@gmail.com', [appointment.customer.email_id], fail_silently=False)

                # ✅ Create notifications
                Notifications.objects.create(
                    user=appointment.customer,
                    provider=appointment.provider,
                    title="Appointment Confirmed",
                    message=f"Your appointment for '{appointment.service.service_name}' has been confirmed by {appointment.provider.name}.",
                    created_at=timezone.now()
                )

                messages.success(request, "Appointment Accepted Successsfully!")

    
    # -----------------
    # Fetching Reviews to Display
    # -----------------
    provider_id = request.session.get("provider_id")
    provider = ServiceProvider.objects.get(provider_id=provider_id)

    reviews = Appointments.objects.filter(
        provider=provider,
        rating__isnull=False
    ).order_by('-app_start_time')


    # Automatically mark completed ones
    now = timezone.now()
    Appointments.objects.filter(
        provider=provider, 
        app_end_time__lt=now
        ).exclude(status__in=["Completed", "Cancelled"]).update(status="Completed")
    

    # Categorize appointments
    pending_apps = Appointments.objects.filter(provider=provider, status="Pending").order_by('-app_start_time')
    confirmed_apps = Appointments.objects.filter(provider=provider, status="Confirmed").order_by('-app_start_time')
    completed_apps = Appointments.objects.filter(provider=provider, status="Completed").order_by('-app_start_time')
    cancelled_apps = Appointments.objects.filter(provider=provider, status="Cancelled").order_by('-app_start_time')

    # Get today's appointments
    today = datetime.today()
    todays_appmnts = Appointments.objects.filter(
        provider=provider,
        app_start_time__date = today
    ).order_by('app_start_time')
    today_schedule = Appointments.objects.filter(
        provider=provider,
        app_start_time__date = today
    ).order_by('app_start_time')[:3]

    # Get recent reviews
    recent_reviews = Appointments.objects.filter(
        provider=provider,
        rating__isnull=False
    ).order_by('app_start_time')[:3]


    yesterday = today - timedelta(days=today.weekday())
    yesterday_appointments = Appointments.objects.filter(provider=provider, app_start_time__date=yesterday)
    today_count = todays_appmnts.count()
    yesterday_count = yesterday_appointments.count()
    # % Change from yesterday
    if yesterday_count > 0:
        appointment_change = round(((today_count - yesterday_count) / yesterday_count) * 100)
    else:
        appointment_change = today_count * 100  # All new appointments

    # Schedule utilization = (booked slots today / total available slots today) * 100
    first_schedule = ProviderSchedule.objects.filter(provider=provider).first()
    total_slots = len(first_schedule.available_time.split(',')) if schedule and first_schedule.available_time else 0
    stat_booked_slots = todays_appmnts.count()
    utilization = round((stat_booked_slots / total_slots) * 100) if total_slots > 0 else 0

    # Avg rating and change from last month
    avg_rating = Appointments.objects.filter(
        provider=provider, status='completed', rating__isnull=False
    ).aggregate(avg=Avg('rating'))['avg'] or 0
    avg_rating = round(avg_rating, 1)

    this_month = Appointments.objects.filter(
        provider=provider, app_start_time__month=today.month, rating__isnull=False
    ).aggregate(avg=Avg('rating'))['avg'] or 0
    last_month = Appointments.objects.filter(
        provider=provider, app_start_time__month=today.month - 1, rating__isnull=False
    ).aggregate(avg=Avg('rating'))['avg'] or 0
    rating_change = round(this_month - last_month, 1)


    # For Customer Overview 
    customers_all = Customer.objects.filter(appointments__provider=provider).distinct()
    total_customers = customers_all.count()
    # Customers who booked this week
    one_week_ago = timezone.now() - timedelta(days=7)
    new_this_week = customers_all.filter(appointments__app_start_time__gte=one_week_ago).distinct().count()
    # Regular customers (more than 2 visits)
    regular_customers = customers_all.annotate(visit_count=Count('appointments')).filter(visit_count__gt=2).count()

    # Retention rate = (regular_customers / total_customers) * 100
    retention_rate = int((regular_customers / total_customers) * 100) if total_customers > 0 else 0
    # Recent activity — last 5 actions from appointments
    recent_activities = (
        Appointments.objects.filter(provider=provider)
        .select_related('customer')
        .order_by('-app_start_time')[:3]
    )

    # Calculating Response Rate
    total_requests = Appointments.objects.filter(provider=provider).count()
    responded = Appointments.objects.filter(provider=provider, status__in=["Confirmed","Cancelled"]).count()
    response_rate = (responded / total_requests * 100) if total_requests > 0 else 0
    response_rate = round(response_rate)

    # Profile views
    viewed_providers = request.session.get("viewed_providers", [])
    if provider_id not in viewed_providers:
        provider.profile_views += 1
    provider.save(update_fields=["profile_views"])
    viewed_providers.append(provider_id)
    request.session["viewed_providers"] = viewed_providers

    # Service Analytics 
    services_analytics = Services.objects.filter(provider_id = provider)
    total_appointments = Appointments.objects.filter(provider=provider).count()
    service_analytics = []
    for service in services_analytics:
        service_count = Appointments.objects.filter(provider=provider, service=service).count()
        percentage = round((service_count / total_appointments * 100), 2) if total_appointments > 0 else 0
        service_analytics.append({
            "name": service.service_name,
            "percentage": percentage
        })

    # ---- Calculating Peak Hours ----
    peak_appointments = Appointments.objects.filter(provider=provider, status__in=["Confirmed", "Completed"])
    peak_time_slots=[
        ('06:00', '09:00'),
        ('09:00', '12:00'),
        ('12:00', '15:00'),
        ('15:00', '18:00'),
        ('18:00', '21:00'),
        ('21:00', '23:59'),
    ]
    slot_counts = Counter()
    for appt in peak_appointments:
        start_time = appt.app_start_time.time()
        for start, end in peak_time_slots:
            start_t = datetime.strptime(start, "%H:%M").time()
            end_t = datetime.strptime(end, "%H:%M").time()
            if start_t <= start_time < end_t:
                slot_counts[f"{start} - {end}"] += 1
                break
    sorted_slots = sorted(slot_counts.items(), key=lambda x: x[1], reverse=True)
    total_bookings = sum(slot_counts.values()) or 1

    peak_data = []
    for i, (slot, count) in enumerate(sorted_slots[:3]):  # top 3 slots only
        percent = (count / total_bookings) * 100
        if i == 0:
            label = "High"
            color = "bg-danger"
        elif i == 1:
            label = "Medium"
            color = "bg-warning"
        else:
            label = "Low"
            color = "bg-success"

        peak_data.append({
            "time_range": slot,
            "label": label,
            "percentage": round(percent, 1),
            "color": color,
        })

    while len(peak_data) < 3:
        peak_data.append({
            "time_range": "00:00 - 00:00",
            "label": "Low",
            "percentage": 0,
            "color": "bg-secondary",
        })

    # Review Analytics
    reviews_all = Appointments.objects.filter(provider=provider, rating__isnull=False)

    total_reviews_now = reviews_all.count()
    avg_rating_now = round(reviews_all.aggregate(avg=Avg('rating'))['avg'] or 0, 1)

    # Count of each rating (1 to 5)
    rating_counts = {
        5: reviews_all.filter(rating=5).count(),
        4: reviews_all.filter(rating=4).count(),
        3: reviews_all.filter(rating=3).count(),
        2: reviews_all.filter(rating=2).count(),
        1: reviews_all.filter(rating=1).count(),
    }

    # Calculate percentage for each rating
    rating_percentages = {}
    for star, count in rating_counts.items():
        rating_percentages[star] = round((count / total_reviews_now) * 100, 1) if total_reviews_now > 0 else 0

    
    
    category = provider.category_name
    context = {
        'provider':provider,
        'all_services':all_services,
        'category':category,
        'schedule_dict':schedule_dict,
        'days_of_week':DAYS_OF_WEEK,
        'services_book':services_book,
        'time_slots':time_slots,
        'selected_date':selected_date,
        'all_customers':all_customers,
        "pending_apps": pending_apps,
        "confirmed_apps": confirmed_apps,
        "completed_apps": completed_apps,
        "cancelled_apps": cancelled_apps,
        "reviews":reviews,
        "todays_appmnts":todays_appmnts,
        "today_schedule":today_schedule,
        "recent_reviews":recent_reviews,
        "utilization":utilization,
        "appointment_change":appointment_change,
        "today_count":today_count,
        "avg_rating":avg_rating,
        "rating_change":rating_change,
        "total_customers":total_customers,
        "new_this_week":new_this_week,
        "regular_customers":regular_customers,
        "retention_rate":retention_rate,
        "recent_activities":recent_activities,
        "response_rate":response_rate,
        "profile_views":provider.profile_views,
        "service_analytics":service_analytics,
        "total_appmts":total_appointments,
        "peak_data":peak_data,
        "rating_percentage":rating_percentages,
        "total_reviews_now":total_reviews_now,
        "rating_counts":rating_counts,
        "avg_rating_now":avg_rating_now
    }

    return render(request, 'provider_dashboard.html', context)


# Another view to get time slots
def get_time_slots(request):
    if request.method == "POST":
        data = json.loads(request.body)
        user_type = request.session.get('user_type')

        if user_type == "customer":
            provider_id = data.get("provider_id")
        elif user_type == "provider":
            provider_id = request.session.get("provider_id")

        selected_service_id= data.get("service_id")
        selected_service = get_object_or_404(Services, service_id=selected_service_id)
        selected_date = data.get("appointment_date")
        print("📅 New date received:", selected_date, "for Provider:", provider_id)

        provider = get_object_or_404(ServiceProvider, provider_id=provider_id)
        weekday = datetime.strptime(selected_date, "%Y-%m-%d").strftime("%A")
        schedule = ProviderSchedule.objects.filter(provider=provider, service=selected_service, day_of_week=weekday).first()
        print("Schedule",schedule)

        time_slots = []
        if schedule and schedule.available_time:
            try:
                duration_min = timedelta(minutes=int(selected_service.duration))
                start_str, end_str = schedule.available_time.split("-")
                start = datetime.strptime(start_str, "%H:%M")
                end = datetime.strptime(end_str, "%H:%M")

                print("Duration", duration_min)

                # ---- Booked times ----
                booked_for_date = schedule.booked_slots.get(selected_date, [])
                booked_intervals = []
                for b in booked_for_date:
                    try:
                        b_start = datetime.strptime(b["start"], "%H:%M")
                        b_end = datetime.strptime(b["end"], "%H:%M")
                        booked_intervals.append((b_start, b_end))
                    except Exception:
                        continue
                    
                print("Booked:", booked_intervals)
                
                while start < end:
                    slot_time = start.strftime("%H:%M")
                    slot_st = start
                    slot_end = start + duration_min
                    slot_end2 = start + timedelta(hours=1)
                    available = True

                    # --- Check total booked minutes in this hour ---
                    booked_minutes = 0
                    for b_start, b_end in booked_intervals:
                        # Only count bookings that overlap within this hour window
                        if b_start < slot_end2 and b_end > slot_st:
                            overlap_start = max(slot_st, b_start)
                            overlap_end = min(slot_end2, b_end)
                            booked_minutes += int((overlap_end - overlap_start).total_seconds() / 60)

                    # --- Mark unavailable if fully booked ---
                    # if not (slot_end2 <= b_start or slot_st >= b_end):
                    #     available = False
                        
                    # if booked_minutes + (duration_min.total_seconds() / 60) > 60:
                    #     available = False
                    print("booked minutes",booked_minutes)
                    free_minutes = 60 - booked_minutes
                    if free_minutes < int(duration_min.total_seconds() / 60):
                        available = False
                    if free_minutes == 0:
                        available = False
                        

                    # ---- Blocked times ----
                    blocked_times = [b for b in schedule.blocked_time if b.get("date") == selected_date]
                    for b in blocked_times:
                        blocked_start = datetime.strptime(b["start"], "%H:%M")
                        if slot_st == blocked_start:
                            available = False
                            break

                    time_slots.append({"time":slot_time, "available":available})
                    
                    start += timedelta(hours=1)
                print("Final ts:", time_slots)

            except Exception as e:
                print("Error in get_time_slots:", e)

        
        print("Final:",time_slots)

        return JsonResponse({"time_slots": time_slots})

    return JsonResponse({"error": "Invalid request"}, status=400)