from rest_framework import viewsets, permissions, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from django.db.models import Count
from django.shortcuts import get_object_or_404

from .models import Task, Subject
from .serializers import TaskSerializer, SubjectSerializer


# ==============================
# Pagination
# ==============================
class TaskPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50


# ==============================
# Subject CRUD
# ==============================
class SubjectViewSet(viewsets.ModelViewSet):
    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer
    permission_classes = [permissions.IsAuthenticated]


# ==============================
# Task CRUD
# ==============================
class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    pagination_class = TaskPagination
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Faqat login bo‘lgan userga tegishli tasklar
        queryset = Task.objects.filter(assignees=self.request.user).select_related(
            'document', 'subject'
        ).prefetch_related('assignees').order_by('-created_at')

        # Status filter query param orqali
        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)

        return queryset

    # ========== LIST with status summary ==========
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)

        # Status bo‘yicha count
        counts = queryset.values('status').annotate(count=Count('id'))
        status_dict = {c['status']: c['count'] for c in counts}
        for s in ['pending', 'in_progress', 'be_rejected', 'done']:
            status_dict.setdefault(s, 0)

        response = {
            "pending": status_dict['pending'],
            "in_progress": status_dict['in_progress'],
            "be_rejected": status_dict['be_rejected'],
            "done": status_dict['done'],
            "results": serializer.data,
            "count": self.paginator.page.paginator.count if page else len(serializer.data),
            "next": self.paginator.get_next_link() if page else None,
            "previous": self.paginator.get_previous_link() if page else None
        }

        return Response(response)

    # ========== CREATE ==========
    def perform_create(self, serializer):
        assignees_ids = self.request.data.get('assignees_ids', [])
        task = serializer.save()  # DB ga saqlash
        if assignees_ids:
            task.assignees.set(assignees_ids)

    # ========== UPDATE ==========
    def perform_update(self, serializer):
        assignees_ids = self.request.data.get('assignees_ids', None)
        task = serializer.save()
        if assignees_ids is not None:
            task.assignees.set(assignees_ids)

    # ========== DESTROY ==========
    def destroy(self, request, *args, **kwargs):
        task = self.get_object()
        task.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
