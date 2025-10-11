from services.models import ProviderSchedule

def reset_provider_schedule():
    # Clear availability and block times for everyone
    from services.models import ProviderSchedule
    ProviderSchedule.objects.all().delete()
