import django_filters
from django.db import transaction
from django.db.models import Count, OuterRef, Q, Subquery
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from flow_task.models import Task
from flow_user.permissions import IsManagerOrReadOnly, is_manager

from .models import AppealForm, AppealForwarding, AppealKind, AppealQuestion, OralAppeal, ReceptionType
from .serializers import (
    ACTIVE_TASK_STATUSES,
    AppealExtendSerializer,
    AppealFormSerializer,
    AppealForwardingSerializer,
    AppealKindSerializer,
    AppealQuestionSerializer,
    OralAppealSerializer,
    ReceptionTypeSerializer,
)

TASK_STATUSES = ("in_progress", "in_confirmation", "be_rejected", "done", "done_overdue")


class AppealPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 50


# ---------- Ma'lumotnomalar ----------
class AppealQuestionViewSet(viewsets.ModelViewSet):
    queryset = AppealQuestion.objects.annotate(
        appeals_count=Count("appeals", distinct=True),
        children_count=Count("children", distinct=True),
    )
    serializer_class = AppealQuestionSerializer
    permission_classes = [IsManagerOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["parent", "is_active"]
    search_fields = ["code", "name"]

    def destroy(self, request, *args, **kwargs):
        # Ichki savollar yoki murojaatlarda ishlatilgan savol o'chirilmaydi (faolsizlantirish tavsiya etiladi)
        question = self.get_object()
        if question.children_count:
            return Response({"detail": "Bo'lim ichida savollar bor. Avval ularni o'chiring yoki bo'limni faolsizlantiring."},
                            status=status.HTTP_400_BAD_REQUEST)
        if question.appeals_count:
            return Response({"detail": f"Savol {question.appeals_count} ta murojaatda ishlatilgan. O'chirish o'rniga faolsizlantiring."},
                            status=status.HTTP_400_BAD_REQUEST)
        return super().destroy(request, *args, **kwargs)



class AppealFormViewSet(viewsets.ModelViewSet):
    queryset = AppealForm.objects.all()
    serializer_class = AppealFormSerializer
    permission_classes = [IsManagerOrReadOnly]


class AppealKindViewSet(viewsets.ModelViewSet):
    queryset = AppealKind.objects.all()
    serializer_class = AppealKindSerializer
    permission_classes = [IsManagerOrReadOnly]


class ReceptionTypeViewSet(viewsets.ModelViewSet):
    queryset = ReceptionType.objects.all()
    serializer_class = ReceptionTypeSerializer
    permission_classes = [IsManagerOrReadOnly]


# ---------- Murojaatlar ----------
def visible_appeals(user):
    """Admin/devonxona - barcha murojaatlar, qolganlar - topshirig'i o'ziga biriktirilganlar."""
    if is_manager(user):
        return OralAppeal.objects.all()
    return OralAppeal.objects.filter(tasks__assignees=user).distinct()


def with_task_info(queryset):
    """Har bir murojaatga oxirgi topshirig'i (id, status, muddat) qo'shiladi."""
    last_task = Task.objects.filter(appeal=OuterRef("pk")).order_by("-created_at")
    return queryset.annotate(
        task_id=Subquery(last_task.values("id")[:1]),
        task_status=Subquery(last_task.values("status")[:1]),
        task_due_date=Subquery(last_task.values("due_date")[:1]),
    )


class OralAppealFilter(django_filters.FilterSet):
    received_from = django_filters.DateFilter(field_name="received_date", lookup_expr="gte")
    received_to = django_filters.DateFilter(field_name="received_date", lookup_expr="lte")
    status = django_filters.CharFilter(method="filter_status")
    overdue = django_filters.BooleanFilter(method="filter_overdue")

    class Meta:
        model = OralAppeal
        fields = ["applicant_type", "appeal_form", "appeal_kind", "reception_type", "question", "department", "reg_year"]

    def filter_status(self, queryset, name, value):
        # "no_task" - topshiriq hali berilmagan murojaatlar
        if value == "no_task":
            return queryset.filter(task_id__isnull=True)
        return queryset.filter(task_status=value)

    def filter_overdue(self, queryset, name, value):
        cond = overdue_q()
        return queryset.filter(cond) if value else queryset.exclude(cond)


def overdue_q():
    today = timezone.localdate()
    return Q(task_status="done_overdue") | Q(task_status__in=ACTIVE_TASK_STATUSES, task_due_date__lt=today)


class OralAppealViewSet(viewsets.ModelViewSet):
    serializer_class = OralAppealSerializer
    pagination_class = AppealPagination
    permission_classes = [IsManagerOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = OralAppealFilter
    search_fields = ["reg_number", "applicant_name", "address", "phone", "summary"]
    ordering_fields = ["created_at", "received_date", "reg_seq"]

    def get_queryset(self):
        return (
            with_task_info(visible_appeals(self.request.user))
            .select_related(
                "question", "appeal_form", "appeal_kind", "reception_type",
                "signer", "extended_by", "department", "closed_by",
            )
            .prefetch_related("forwardings__sent_to")
        )

    def list(self, request, *args, **kwargs):
        # Statistika: filtrlardan tashqari umumiy sanoq (topshiriqlar sahifasidagidek)
        base = with_task_info(visible_appeals(request.user))
        stats = base.aggregate(
            all_appeals=Count("id"),
            no_task=Count("id", filter=Q(task_id__isnull=True)),
            overdue=Count("id", filter=overdue_q()),
            **{name: Count("id", filter=Q(task_status=name)) for name in TASK_STATUSES},
        )
        response = super().list(request, *args, **kwargs)
        response.data.update(stats)
        return response

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=["post"])
    def extend(self, request, pk=None):
        """Muddatni uzaytirish: yakunlanmagan topshiriqlar muddati yangilanadi, dastlabki muddat saqlanadi."""
        appeal = self.get_object()
        serializer = AppealExtendSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_due = serializer.validated_data["new_due_date"]

        with transaction.atomic():
            tasks = list(Task.objects.select_for_update().filter(appeal=appeal).order_by("created_at"))
            open_tasks = [t for t in tasks if t.status in ACTIVE_TASK_STATUSES]
            if not open_tasks:
                return Response(
                    {"detail": "Muddatni uzaytirish uchun murojaatda yakunlanmagan topshiriq bo'lishi kerak."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if appeal.original_due_date is None:
                appeal.original_due_date = open_tasks[0].due_date
            appeal.extended_due_date = new_due
            appeal.extended_by = serializer.validated_data["extended_by"]
            appeal.extended_at = timezone.now()
            appeal.save(update_fields=["original_due_date", "extended_due_date", "extended_by", "extended_at", "updated_at"])
            Task.objects.filter(id__in=[t.id for t in open_tasks]).update(due_date=new_due)

        return Response(self.get_serializer(self.get_queryset().get(pk=appeal.pk)).data)


class AppealForwardingViewSet(viewsets.ModelViewSet):
    serializer_class = AppealForwardingSerializer
    permission_classes = [IsManagerOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["appeal"]

    def get_queryset(self):
        return AppealForwarding.objects.filter(
            appeal__in=visible_appeals(self.request.user).values("id")
        ).select_related("sent_to")
