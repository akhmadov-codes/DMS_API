from django.core.management.base import BaseCommand
from django.utils import timezone
from flow_task.models import Task

class Command(BaseCommand):
    help = 'Muddati o`tgan vazifalarni rad etish'

    def handle(self, *args, **options):
        today = timezone.localtime().date()
        updated = Task.objects.filter(
            due_date__lt=today, 
            status__in=['in_progress', 'in_confirmation']
        ).update(status='be_rejected')
        
        self.stdout.write(f"{updated} ta vazifa yangilandi.")