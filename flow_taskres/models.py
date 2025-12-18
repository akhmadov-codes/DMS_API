from django.db import models
from flow_task.models import Task
from flow_user.models import CustomUser

class TaskResponse(models.Model):
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name='responses'
    )
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='task_responses'
    )
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Response for Task {self.task.id}"

class TaskResponseFile(models.Model):
    response = models.ForeignKey(
        TaskResponse,
        on_delete=models.CASCADE,
        related_name='files'
    )
    file = models.FileField(upload_to='task_response_files/')
    extension = models.CharField(max_length=10, null=True, blank=True)
    def save(self, *args, **kwargs):
        if self.file and not self.extension:
            self.extension = self.file.name.split('.')[-1]
        super().save(*args, **kwargs)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"File for Response {self.response.id}"