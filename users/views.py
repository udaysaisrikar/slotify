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
from django.http import JsonResponse
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



# Customer Dashboard
def customer_dashboard(request):
    if 'customer_id' not in request.session:
        return redirect('home')
    
    customer_id = request.session.get('customer_id')
    customer = Customer.objects.get(customer_id = customer_id)
    
    providers = ServiceProvider.objects.all()
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
        selected_date = request.POST.get('appointment_date')
        time_slots = []
        if selected_date:
            # find schedule by weekday
            weekday = datetime.strptime(selected_date, "%Y-%m-%d").strftime("%A")
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

    context = {
        'providers':providers,
        'customer':customer,
        'services':services,
        'time_slots':time_slots,
        'selected_date':selected_date,
        'selected_provider':selected_provider
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
            # Update Provider
            provider.name = name
            provider.email_id = email_id
            provider.phone_no = phone_no
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
    services = Services.objects.filter(provider_id=provider)
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
                for service in services:
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
                for service in services:
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


    # Passing Services to Book Appointment
    provider_id = request.session.get('provider_id')
    services_book = None
    if provider_id:
        provider = get_object_or_404(ServiceProvider, provider_id=provider_id)
        services_book = Services.objects.filter(provider_id=provider)

        # ----- Displaying time slots -----
        selected_date = datetime.today().date()
        
        time_slots = []
        if selected_date:
            # find schedule by weekday
            weekday = selected_date.strftime("%A")
            schedule = ProviderSchedule.objects.filter(provider=provider, day_of_week=weekday).first()
            if schedule and schedule.available_time:
                try:
                    start_str, end_str = schedule.available_time.split("-")
                    start = datetime.strptime(start_str, "%H:%M")
                    end = datetime.strptime(end_str, "%H:%M")
                    # Build all hourly slots
                    while start < end:
                        slot_st = start,
                        slot_end = start + timedelta(hours=1),
                        slot_time = start.strftime("%H:%M")
                        # Initially
                        available = True
                       
                       # Check blocked times
                        for b in schedule.blocked_time or []:
                            if b["date"] == selected_date:
                                block_start = datetime.strptime(b["start"], "%H:%M")
                                
                                # Check if slot overlaps with blocked time
                                print(block_start)
                                if not (slot_end <= block_start):
                                    available = False
                                    break

                        # Check Booked Slots
                        booked_for_date = schedule.booked_slots.get(selected_date, [])
                        for booked in booked_for_date:
                            booked_start = datetime.strptime(booked["start"], "%H:%M")
                            booked_end = datetime.strptime(booked["end"], "%H:%M")
                            if not (slot_end <= booked_start or slot_st >= booked_end):
                                available = False
                                break
                        
                        time_slots.append({
                            "time": slot_time,
                            "available": available
                        })

                        start += timedelta(hours=1)

                except Exception as e:
                    print("Error:",e)

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


    # ---------------
    # Handle Appointments Display
    # ---------------
    
    category = provider.category_name
    context = {
        'provider':provider,
        'services':services,
        'category':category,
        'schedule_dict':schedule_dict,
        'days_of_week':DAYS_OF_WEEK,
        'services_book':services_book,
        'time_slots':time_slots,
        'selected_date':selected_date
    }

    return render(request, 'provider_dashboard.html', context)