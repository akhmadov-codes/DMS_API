from rest_framework import viewsets, permissions
from django.shortcuts import get_object_or_404

from .models import TaskResponse, TaskResponseFile
from .serializers import TaskResponseSerializer, TaskResponseFileSerializer
from flow_task.models import Task


# -------------------------------
# TaskResponse ViewSet
# -------------------------------
class TaskResponseViewSet(viewsets.ModelViewSet):
    serializer_class = TaskResponseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Faqat ma'lum task_id ga tegishli responses
        ?task_id=<id>
        """
        task_id = self.request.query_params.get('task_id')
        if not task_id:
            return TaskResponse.objects.none()
        return TaskResponse.objects.filter(task_id=task_id).select_related('user').prefetch_related('files').order_by('-created_at')

    def perform_create(self, serializer):
        """
        TaskResponse yaratish:
        - task_id request.data orqali olinadi
        - user avtomatik request.user
        """
        task_id = self.request.data.get('task_id')
        task = get_object_or_404(Task, id=task_id)
        serializer.save(user=self.request.user, task=task)


# -------------------------------
# TaskResponseFile ViewSet
# -------------------------------
class TaskResponseFileViewSet(viewsets.ModelViewSet):
    serializer_class = TaskResponseFileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Faqat ma'lum response_id ga tegishli fayllar
        ?response_id=<id>
        """
        response_id = self.request.query_params.get('response_id')
        if not response_id:
            return TaskResponseFile.objects.none()
        return TaskResponseFile.objects.filter(response_id=response_id).order_by('-uploaded_at')

    def perform_create(self, serializer):
        """
        Fayl yaratish:
        - response_id request.data orqali olinadi
        """
        response_id = self.request.data.get('response_id')
        response = get_object_or_404(TaskResponse, id=response_id)
        serializer.save(response=response)
