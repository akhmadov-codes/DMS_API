from rest_framework import viewsets, permissions
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from django.db.models import Count, Q
from .models import Task, Subject
from flow_user.models import CustomUser
from .serializers import TaskSerializer, SubjectSerializer
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
import django_filters
# Pagination
class TaskPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50

# Subject CRUD
class SubjectViewSet(viewsets.ModelViewSet):
    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer
    permission_classes = [permissions.IsAuthenticated]

# Task CRUD
class TaskFilter(django_filters.FilterSet):
    status = django_filters.CharFilter(field_name="status")
    due_date = django_filters.DateFilter(field_name="due_date")
    assignee = django_filters.NumberFilter(field_name="assignees__id")
    created_at = django_filters.DateFilter(field_name="created_at", lookup_expr='date')
    class Meta:
        model = Task
        fields = ['status', 'due_date', 'assignee', 'created_at']

class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    pagination_class = TaskPagination
    permission_classes = [permissions.IsAuthenticated]
    # filterlarni ulash
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = TaskFilter
    search_fields = ['document__title', 'description', 'document__in_number']
    ordering_fields = ['created_at', 'due_date']

    def get_queryset(self):
        user = self.request.user
        # Ruxsatlar (bu qism o'zgarmaydi)
        if user.groups.filter(name__in=['admin', 'devonxona']).exists():
            queryset = Task.objects.all()
        else:
            queryset = Task.objects.filter(assignees=user)
        # Faqat optimallashtirish qoladi
        return queryset.select_related(
            'document', 'subject',
            'document__delivery_type', 'document__document_type',
            'document__journal', 'document__sender'
        ).prefetch_related(
            'assignees',
            'responses__user',
            'responses__files',
            'document__attachments'
        ).distinct()

    def list(self, request, *args, **kwargs):
        # 1. Statistika (Filtrlardan tashqari umumiy sanoq)
        user = request.user
        stat_qs = Task.objects.all() if user.groups.filter(name__in=['admin', 'devonxona']).exists() else Task.objects.filter(assignees=user)
        stats = stat_qs.aggregate(
            all_tasks=Count('id'),
            in_progress=Count('id', filter=Q(status='in_progress')),
            in_confirmation=Count('id', filter=Q(status='in_confirmation')),
            be_rejected=Count('id', filter=Q(status='be_rejected')),
            done=Count('id', filter=Q(status='done'))
        )
        # 2. DjangoFilterBackend avtomatik filtrlangan querysetni beradi
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response = self.get_paginated_response(serializer.data)
            response.data.update(stats)
            return response
        serializer = self.get_serializer(queryset, many=True)
        return Response({**stats, "results": serializer.data})

    def perform_create(self, serializer):
        # 1. validated_data dan assignees_ids ni sug'urib olamiz (pop)
        # Shunda Task modeliga ortiqcha argument bo'lib kirmaydi
        assignees_data = serializer.validated_data.pop('assignees_ids', [])
        # 2. Taskni saqlaymiz
        task = serializer.save()
        # 3. Ijrochilarni qo'lda biriktiramiz
        self._handle_assignees(task, assignees_data)

    def perform_update(self, serializer):
        # Update jarayonida ham pop qilish shart
        assignees_data = serializer.validated_data.pop('assignees_ids', [])
        task = serializer.save()
        self._handle_assignees(task, assignees_data)

    def _handle_assignees(self, task, assignees_data):
        # Ma'lumot validated_data dan kelyapti (bu xavfsizroq)
        if 'all-users' in assignees_data:
            all_users = CustomUser.objects.filter(is_active=True)
            task.assignees.set(all_users)
        elif assignees_data:
            # Agar IDlar ro'yxati kelsa (masalan [1, 2])
            task.assignees.set(assignees_data)
