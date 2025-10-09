from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.hashers import make_password, check_password
from .models import Customer, ServiceProvider
from services.models import ServiceCategory
from django.core.mail import send_mail
from django.db import transaction
# Create your views here.


def customer_dashboard(request):
    if 'customer_id' not in request.session:
        return redirect('home')
    
    customer_id = request.session.get('customer_id')
    customer_name = request.session.get('customer_fname')
    customer = Customer.objects.get(customer_id = customer_id)
    return render(request, 'customer_dashboard.html', {'customer':customer})

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



def provider_dashboard(request):
    provider_id = request.session.get('provider_id')
    if not provider_id:
        return redirect('home')
    
    provider = ServiceProvider.objects.get(provider_id=provider_id)
    return render(request, 'provider_dashboard.html',{'provider':provider})

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
            customer.first_name = request.POST.get('first_name')
            customer.last_name = request.POST.get('last_name')
            customer.email_id = request.POST.get('email_id')
            customer.phone_no = request.POST.get('phone_no')
            dob = request.POST.get('dob')
            if dob:
                customer.dob = dob
            customer.save()
            messages.success(request, "Profile updated successfully!")

        elif user_type == 'provider':
            provider = ServiceProvider.objects.get(provider_id=sp_id)
            email = provider.email_id
            category = provider.category_name
            provider.name = request.POST.get('name')
            provider.email_id = email
            provider.phone_no = request.POST.get('phone_no')
            provider.category_name = category
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