from django.shortcuts import render

# Create your views here.
def book_appointment_view(request):
    return render(request, 'book_appointment.html')