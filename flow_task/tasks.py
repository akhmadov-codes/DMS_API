from celery import shared_task
from django.utils import timezone
from .models import Task

@shared_task
def check_overdue_tasks():
    today = timezone.now().date()
    # Muddati o'tgan va hali yopilmagan vazifalarni topish
    updated_count = Task.objects.filter(
        due_date__lt=today,
        status__in=['in_progress', 'in_confirmation']
    ).update(status='be_rejected')
    
    return f"{updated_count} ta vazifa rad etildi (muddati o'tgan)."