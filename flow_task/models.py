from django.db import models
from django.utils import timezone

from flow_document.models import IncomingDocument
from flow_user.models import CustomUser


class Subject(models.Model):
    title = models.CharField(max_length=250, verbose_name="Mavzu nomi")
    def __str__(self):
        return self.title
    
class TaskDescription(models.Model):
    title = models.CharField(max_length=250, blank=True, null=True)
    def __str__(self):
        return f'{self.title}'


class Task(models.Model):
    STATUS_CHOICES = [
        ("in_progress", "Bajarilmoqda"),
        ("in_confirmation", "Tasdiqlashda"),
        ("be_rejected", "Rad etildi"),
        ("done", "Bajarildi"),
        ("done_overdue", "Muddati o'tib bajarildi"),
    ]
    PRIORITY_CHOICES = [
        ("low", "Past"),
        ("medium", "O'rta"),
        ("high", "Yuqori"),
        ("urgent", "Shoshilinch"),
    ]
    document = models.ForeignKey(IncomingDocument, on_delete=models.CASCADE, related_name="tasks", null=True, blank=True)
    subject = models.ForeignKey(Subject, on_delete=models.SET_NULL, related_name="tasks", null=True, blank=True)
    creator = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, related_name="created_tasks", null=True, blank=True, verbose_name="Topshiriq beruvchi")
    description = models.TextField(blank=True, null=True)
    task_description = models.ForeignKey(TaskDescription, on_delete=models.CASCADE, null=True, blank=True, related_name='tasks', default='Topshiriq o\'z vaqtida ijrosi ta\'minlansin.')
    due_date = models.DateField(blank=True, null=True, verbose_name="Muddati")
    priority = models.CharField( max_length=10, choices=PRIORITY_CHOICES, default="medium")
    assignees = models.ManyToManyField( CustomUser, related_name="assigned_tasks", blank=True, verbose_name="Mas'ullar")
    status = models.CharField( max_length=20, choices=STATUS_CHOICES, default="in_progress")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def is_overdue(self):
        """Muddati o'tganligini tekshirish (dinamik)"""
        if (
            self.due_date
            and self.due_date < timezone.now().date()
            and self.status != "done"
        ):
            return True
        return False

    def __str__(self):
        return f"{self.subject} - {self.status}"
