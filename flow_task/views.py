import django_filters
from django.db.models import Count, Prefetch, Q
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.exceptions import PermissionDenied
from rest_framework import filters, viewsets
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.response import Response

from flow_appeal.models import OralAppeal
from flow_user.permissions import (
    IsManagerOrReadOnly,
    IsManagerRectorOrReadOnly,
    is_manager,
    is_rector,
)

from .models import Subject, Task, TaskAssignee, TaskDescription
from .serializers import SubjectSerializer, TaskDescriptionSerializer, TaskSerializer


class TaskPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 50


class TaskPermission(BasePermission):
    """
    O'qish        - barcha kirganlar (ro'yxat get_queryset'da cheklanadi)
    Yaratish/tahrir - admin, devonxona yoki rektor
    O'chirish     - admin yoki devonxona
    """

    message = "Sizda bu amal uchun ruxsat yo'q."

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return True
        if request.method == "DELETE":
            return is_manager(user)
        return is_manager(user) or is_rector(user)


# Mavzu (Subject) CRUD
class SubjectViewSet(viewsets.ModelViewSet):
    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer
    permission_classes = [IsManagerOrReadOnly]


# Topshiriq mazmuni CRUD (rektor topshiriq formasidan yangisini qo'sha oladi)
class TaskdiscriptionViewSet(viewsets.ModelViewSet):
    queryset = TaskDescription.objects.all()
    serializer_class = TaskDescriptionSerializer
    permission_classes = [IsManagerRectorOrReadOnly]


class TaskFilter(django_filters.FilterSet):
    status = django_filters.CharFilter(field_name="status")
    due_date = django_filters.DateFilter(field_name="due_date")
    assignee = django_filters.NumberFilter(field_name="assignees__id")
    created_at = django_filters.DateFilter(field_name="created_at", lookup_expr="date")
    appeal = django_filters.NumberFilter(field_name="appeal_id")
    document = django_filters.NumberFilter(field_name="document_id")
    # Taqvim uchun muddat oralig'i (YYYY-MM-DD, ikkala chegara ham kiradi)
    due_from = django_filters.DateFilter(field_name="due_date", lookup_expr="gte")
    due_to = django_filters.DateFilter(field_name="due_date", lookup_expr="lte")
    # kind=document - hujjat bo'yicha, kind=appeal - og'zaki murojaat bo'yicha topshiriqlar
    kind = django_filters.ChoiceFilter(method="filter_kind", choices=[("document", "document"), ("appeal", "appeal")])

    class Meta:
        model = Task
        fields = ["status", "due_date", "assignee", "created_at", "appeal", "document", "due_from", "due_to", "kind"]

    def filter_kind(self, queryset, name, value):
        return queryset.filter(appeal__isnull=(value != "appeal"))


class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    pagination_class = TaskPagination
    permission_classes = [TaskPermission]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = TaskFilter
    search_fields = ["document__title", "description", "document__in_number", "appeal__reg_number", "appeal__applicant_name"]
    ordering_fields = ["created_at", "due_date"]

    def _visible_tasks(self):
        """Admin/devonxona - barcha topshiriqlar, qolganlar - o'ziga biriktirilganlar."""
        user = self.request.user
        if is_manager(user):
            return Task.objects.all()
        return Task.objects.filter(assignees=user)

    def get_queryset(self):
        return (
            self._visible_tasks()
            .select_related(
                "document",
                "subject",
                "task_description",
                "document__delivery_type",
                "document__document_type",
                "document__journal",
                "document__sender",
                "document__signer_type",
                "appeal__question",
                "appeal__appeal_form",
                "appeal__appeal_kind",
                "appeal__reception_type",
                "appeal__signer",
                "appeal__department",
            )
            .prefetch_related(
                Prefetch(
                    "taskassignee_set",
                    queryset=TaskAssignee.objects.select_related("user__department").order_by("order"),
                ),
                "responses__user",
                "responses__files",
                "document__attachments",
            )
            .distinct()
        )

    def list(self, request, *args, **kwargs):
        # 1. Statistika (filtrlardan tashqari umumiy sanoq)
        stats = self._visible_tasks().aggregate(
            all_tasks=Count("id"),
            in_progress=Count("id", filter=Q(status="in_progress")),
            in_confirmation=Count("id", filter=Q(status="in_confirmation")),
            be_rejected=Count("id", filter=Q(status="be_rejected")),
            done=Count("id", filter=Q(status="done")),
            done_overdue=Count("id", filter=Q(status="done_overdue")),
        )
        # 2. Filtrlangan va sahifalangan ro'yxat
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
        serializer.save(creator=self.request.user)

    def perform_update(self, serializer):
        # Ijroni tasdiqlash/qaytarish (status) - faqat admin yoki devonxona.
        # Rektor topshiriqni tahrirlay oladi, lekin statusini o'zgartira olmaydi.
        if "status" in serializer.validated_data and not is_manager(self.request.user):
            raise PermissionDenied("Topshiriq holatini faqat admin yoki devonxona o'zgartira oladi.")
        task = serializer.save()
        # "Bajarildi" qilinganda oxirgi javob muddatdan keyin bo'lsa - "Muddati o'tib bajarildi"
        if task.status == "done" and task.due_date:
            last_response = task.responses.order_by("-created_at").first()
            if last_response:
                response_date = last_response.created_at.date()
                if response_date > task.due_date:
                    task.status = "done_overdue"
                    task.save(update_fields=["status"])
        # Og'zaki murojaat: nazoratdan kim va qachon olgani qayd etiladi
        if task.appeal_id and task.status in ("done", "done_overdue"):
            OralAppeal.objects.filter(pk=task.appeal_id, closed_at__isnull=True).update(
                closed_by=self.request.user, closed_at=timezone.now()
            )
