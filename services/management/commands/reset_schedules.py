from django.core.management.base import BaseCommand
from services.models import ProviderSchedule

class Command(BaseCommand):
    help = "Reset provider schedules every sunday midnight"

    def handle(self, *args, **kwargs):
        ProviderSchedule.objects.update(
            available_time = "",
            blocked_time = [],
            booked_slots = {}
        )

        self.stdout.write(self.style.SUCCESS("Provider Schedules reset Successfully"))