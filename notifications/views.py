from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from .models import Notifications
from users.models import Customer

# Create your views here.
# @login_required
def mark_all_as_read(request):
    cus_id = request.session.get('customer_id')
    customer = get_object_or_404(Customer, customer_id = cus_id)
    Notifications.objects.filter(user=customer, is_read=False).update(is_read=True)
    return JsonResponse({"success": True})