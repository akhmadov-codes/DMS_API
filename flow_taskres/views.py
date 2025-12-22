from rest_framework import viewsets, permissions, mixins, status, generics
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import TaskResponse, TaskResponseFile
from .serializers import TaskResponseSerializer
from flow_task.models import Task

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
        # Vue dan kelayotgan task_id orqali Taskni topish
        task_id = self.request.data.get('task_id')
        task = get_object_or_404(Task, id=task_id)
        
        # Userni avtomatik biriktirish
        response_obj = serializer.save(user=self.request.user, task=task)

        # MUHIM: Vazifa statusini avtomatik "done"ga o'tkazish
        if task.status != 'done':
            task.status = 'done'
            task.save()

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        # Faqat o'z javobini yoki admin o'chira olishi uchun
        if instance.user != request.user and not request.user.groups.filter(name__in=['admin', 'devonxona']).exists():
            return Response(
                {"detail": "Siz faqat o'z javobingizni o'chira olasiz."}, 
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)