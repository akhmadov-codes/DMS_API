from rest_framework import viewsets, permissions, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from django.db.models import Count
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
        
        # 1. Permission asosida boshlang'ich queryset
        if user.groups.filter(name__in=['admin', 'devonxona']).exists():
            queryset = Task.objects.all()
        else:
            # 2. Oddiy foydalanuvchi faqat o'zi ijrochi bo'lgan tasklarni ko'radi
            # .distinct() takroriy tasklar chiqib qolishining oldini oladi
            queryset = Task.objects.filter(assignees=user).distinct()

        # 2. OPTIMIZATSIYA (select_related va prefetch_related)
        # Bitta so'rovda Task -> Document -> Responses -> Files hammasini olib keladi
        queryset = queryset.select_related(
            'document', 
            'subject', 
            'document__delivery_type', 
            'document__document_type', 
            'document__journal', 
            'document__sender'
        ).prefetch_related(
            'assignees', 
            'responses__user',      # TaskResponse'ni kim yozganini olish
            'responses__files',     # TaskResponse'ga tegishli fayllarni olish
            'document__attachments' # Asosiy hujjat fayllarini olish
        ).distinct().order_by('-created_at')

        # 3. Filtrlash (Query Params)
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
        user = request.user
        
        # 1. Statistika uchun yengil query
        if user.groups.filter(name__in=['admin', 'devonxona']).exists():
            stat_qs = Task.objects.all()
        else:
            stat_qs = Task.objects.filter(assignees=user)

        counts = stat_qs.values('status').annotate(count=Count('id'))
        status_dict = {c['status']: c['count'] for c in counts}
        for s in ['in_progress', 'be_rejected', 'done']:
            status_dict.setdefault(s, 0)

        # 2. Asosiy ma'lumotlarni olish
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            # Standart paginatsiyani chaqiramiz
            response = self.get_paginated_response(serializer.data)
            # Paginatsiya natijasiga (response.data) statistika maydonlarini qo'shamiz
            response.data['in_progress'] = status_dict['in_progress']
            response.data['be_rejected'] = status_dict['be_rejected']
            response.data['done'] = status_dict['done']
            return response

        # Agar paginatsiya ishlamasa (masalan, hamma ma'lumot bitta sahifada bo'lsa)
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            "in_progress": status_dict['in_progress'],
            "be_rejected": status_dict['be_rejected'],
            "done": status_dict['done'],
            "count": queryset.count(),
            "results": serializer.data
        })

    # ========== CREATE ==========
    def perform_create(self, serializer):
        assignees_ids = self.request.data.get('assignees_ids', [])
        task = serializer.save()
        if assignees_ids:
            task.assignees.set(assignees_ids)

    # ========== UPDATE ==========
    def perform_update(self, serializer):
        assignees_ids = self.request.data.get('assignees_ids', None)
        task = serializer.save()
        if assignees_ids is not None:
            task.assignees.set(assignees_ids)