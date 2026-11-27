from django.db import transaction
from rest_framework import generics, mixins, permissions, viewsets

from flow_user.permissions import is_manager

from .models import TaskResponse, TaskResponseFile
from .serializers import TaskResponseSerializer


class IsResponseOwnerOrManager(permissions.BasePermission):
    """Javob fayli faqat javob egasi yoki admin/devonxona tomonidan o'chiriladi."""

    message = "Sizda bu amal uchun ruxsat yo'q."

    def has_object_permission(self, request, view, obj):
        return obj.response.user_id == request.user.id or is_manager(request.user)


class TaskResponseFileDeleteView(generics.DestroyAPIView):
    queryset = TaskResponseFile.objects.select_related("response")
    permission_classes = [permissions.IsAuthenticated, IsResponseOwnerOrManager]


class TaskResponseViewSet(mixins.CreateModelMixin, mixins.UpdateModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
    queryset = TaskResponse.objects.select_related("task", "user").prefetch_related("files")
    serializer_class = TaskResponseSerializer
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    def _mark_in_confirmation(task):
        if task.status != 'in_confirmation':
            task.status = 'in_confirmation'
            task.save(update_fields=['status', 'updated_at'])

    def perform_create(self, serializer):
        task = serializer.validated_data.get('task')
        with transaction.atomic():
            serializer.save(user=self.request.user)
            self._mark_in_confirmation(task)

    def perform_update(self, serializer):
        # PATCH'da "task" yuborilmasa, javobning o'z topshirig'i olinadi
        task = serializer.validated_data.get('task') or serializer.instance.task
        with transaction.atomic():
            serializer.save()
            self._mark_in_confirmation(task)

    def check_object_permissions(self, request, obj):
        """Tahrirlash va o'chirish faqat egasi yoki admin uchun"""
        super().check_object_permissions(request, obj)
        if self.action in ['update', 'partial_update', 'destroy']:
            if obj.user_id != request.user.id and not is_manager(request.user):
                self.permission_denied(request, message="Sizda bu amal uchun ruxsat yo'q.")
