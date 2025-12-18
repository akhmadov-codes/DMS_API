from rest_framework import viewsets, mixins, serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import TaskResponse, TaskResponseFile
from .serializers import TaskResponseSerializer
from flow_task.models import Task

class TaskResponseViewSet(mixins.ListModelMixin,
                          mixins.CreateModelMixin,
                          viewsets.GenericViewSet):
    serializer_class = TaskResponseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        task_id = self.kwargs.get('task_id')
        return TaskResponse.objects.filter(
            task_id=task_id,
            user=self.request.user
        )

    def perform_create(self, serializer):
        task_id = self.kwargs.get('task_id')
        task = get_object_or_404(Task, id=task_id)

        # Max 1 response per user (optional)
        if TaskResponse.objects.filter(task=task, user=self.request.user).exists():
            raise serializers.ValidationError("Siz bu taskga javob allaqachon yaratgansiz.")

        # DB ga saqlash
        response = TaskResponse.objects.create(
            task=task,
            user=self.request.user,
            description=serializer.validated_data.get('description', '')
        )

        # Fayllarni saqlash
        for f in self.request.FILES.getlist('uploaded_files'):
            TaskResponseFile.objects.create(response=response, file=f)

        # Agar kerak bo‘lsa, return qilsa bo‘ladi
        return response
