from rest_framework import viewsets, permissions
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from django.db.models import Count
from .models import Task, Subject
from .serializers import TaskSerializer, SubjectSerializer

class TaskPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50

class SubjectViewSet(viewsets.ModelViewSet):
    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer
    permission_classes = [permissions.IsAuthenticated]

class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    pagination_class = TaskPagination
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Faqat login bo‘lgan userga tegishli tasklar
        queryset = Task.objects.filter(assignees=self.request.user).order_by('-created_at')
        # Status filter query param orqali
        status = self.request.query_params.get('status')
        if status:
            queryset = queryset.filter(status=status)
        return queryset

    def list(self, request, *args, **kwargs):
        """
        /api/tasks/
        - Paginated task list
        - Status bo‘yicha count
        - Optional status filter (?status=pending)
        """
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)

        # Status bo‘yicha count (shuningdek filter bilan ishlaydi)
        counts = queryset.values('status').annotate(count=Count('id'))
        status_dict = {c['status']: c['count'] for c in counts}
        for s in ['pending', 'in_progress', 'be_rejected', 'done']:
            status_dict.setdefault(s, 0)

        response = {
            **status_dict,
            'results': serializer.data
        }

        return self.get_paginated_response(response)
