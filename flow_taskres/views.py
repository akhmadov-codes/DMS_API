from rest_framework import viewsets, permissions, mixins, generics
from rest_framework.response import Response
from .models import TaskResponse, TaskResponseFile
from .serializers import TaskResponseSerializer
from django.db import transaction

class TaskResponseFileDeleteView(generics.DestroyAPIView):
    queryset = TaskResponseFile.objects.all()
    permission_classes = [permissions.IsAuthenticated]

class TaskResponseViewSet(mixins.CreateModelMixin, 
                          mixins.UpdateModelMixin, 
                          mixins.DestroyModelMixin, 
                          viewsets.GenericViewSet):
    queryset = TaskResponse.objects.all()
    serializer_class = TaskResponseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        # Serializer validated_data'dan taskni olamiz
        task = serializer.validated_data.get('task')
        with transaction.atomic():
            # 1. Javobni saqlaymiz (user avtomatik birikadi)
            serializer.save(user=self.request.user)
            # 2. Task statusini yangilaymiz
            if task.status != 'in_confirmation':
                task.status = 'in_confirmation'
                task.save(update_fields=['status', 'updated_at'])
    def perform_update(self, serializer):
        # Tahrirlashda ham tranzaksiyadan foydalanamiz
        task = serializer.validated_data.get('task')
        with transaction.atomic():
            serializer.save()
            if task.status != 'in_confirmation':
                task.status = 'in_confirmation'
                task.save(update_fields=['status', 'updated_at'])

    def check_object_permissions(self, request, obj):
        """Tahrirlash va o'chirish faqat egasi yoki admin uchun"""
        super().check_object_permissions(request, obj)
        if self.action in ['update', 'partial_update', 'destroy']:
            is_admin = request.user.groups.filter(name__in=['admin', 'devonxona']).exists()
            if obj.user != request.user and not is_admin:
                self.permission_denied(request, message="Sizda bu amal uchun ruxsat yo'q.")