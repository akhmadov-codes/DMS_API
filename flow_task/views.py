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
        user = self.request.user
        # Agar foydalanuvchi admin yoki devonxona bo'lsa → barcha tasklar
        if user.groups.filter(name__in=['admin', 'devonxona']).exists():
            queryset = Task.objects.all()
        else:
            # Aks holda faqat assignees ichida bo‘lgan tasklar
            queryset = Task.objects.filter(assignees=user)
        # select_related / prefetch_related optimallashtirish
        queryset = queryset.select_related('document', 'subject').prefetch_related('assignees').order_by('-created_at')
        # Qo‘shimcha filterlar query param orqali
        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)
        due_date_param = self.request.query_params.get('due_date')
        if due_date_param:
            queryset = queryset.filter(due_date=due_date_param)
        assignee_param = self.request.query_params.get('assignee')
        if assignee_param:
            queryset = queryset.filter(assignees__id=assignee_param)
        created_at_param = self.request.query_params.get('created_at')
        if created_at_param:
            queryset = queryset.filter(created_at__date=created_at_param)

        return queryset


    # ========== LIST with status summary ==========
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)

        # Status bo‘yicha count
        counts = queryset.values('status').annotate(count=Count('id'))
        status_dict = {c['status']: c['count'] for c in counts}
        for s in ['in_progress', 'be_rejected', 'done']:
            status_dict.setdefault(s, 0)

        response = {
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
