import os
from django.db import models
from flow_task.models import Task
from flow_user.models import CustomUser

class TaskResponse(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='responses')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='task_responses')
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Response by {self.user.first_name} for Task {self.task.id}"

class TaskResponseFile(models.Model):
    response = models.ForeignKey(TaskResponse, on_delete=models.CASCADE, related_name='files')
    file = models.FileField(upload_to='task_response_files/%Y/%m/%d/')
    extension = models.CharField(max_length=10, null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.file and not self.extension:
            _, ext = os.path.splitext(self.file.name)
            self.extension = ext.replace('.', '').lower()
        super().save(*args, **kwargs)