from django.utils import timezone
from rest_framework import serializers

from flow_document.models import Sender, Signer
from flow_document.serializers import SenderSerializer, SignerSerializer
from flow_user.models import Department

from .models import AppealForm, AppealForwarding, AppealKind, AppealQuestion, OralAppeal, ReceptionType

# Topshiriq hali yakunlanmagan holatlar (muddat buzilganini hisoblash uchun)
ACTIVE_TASK_STATUSES = ("in_progress", "in_confirmation", "be_rejected")


class AppealQuestionSerializer(serializers.ModelSerializer):
    parent_id = serializers.PrimaryKeyRelatedField(
        queryset=AppealQuestion.objects.all(), source="parent", required=False, allow_null=True
    )

    # Boshqaruv sahifasi uchun (ro'yxat queryset'ida annotatsiya qilinadi)
    appeals_count = serializers.IntegerField(read_only=True, default=0)
    children_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = AppealQuestion
        fields = ["id", "code", "name", "parent_id", "is_active", "appeals_count", "children_count"]

    def validate_code(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Kod bo'sh bo'lishi mumkin emas.")
        return value

    def validate_parent_id(self, parent):
        # Halqa (o'zi yoki o'z avlodi ota-bo'lim bo'lishi) oldi olinadi
        node = parent
        while node is not None and self.instance is not None:
            if node.pk == self.instance.pk:
                raise serializers.ValidationError("Savol o'zi yoki o'z ichki bo'limi ostiga joylanishi mumkin emas.")
            node = node.parent
        return parent


class AppealFormSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppealForm
        fields = ["id", "name"]


class AppealKindSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppealKind
        fields = ["id", "name"]


class ReceptionTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReceptionType
        fields = ["id", "name"]


class _DepartmentShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ["id", "name"]


class AppealForwardingSerializer(serializers.ModelSerializer):
    sent_to = SenderSerializer(read_only=True)
    appeal_id = serializers.PrimaryKeyRelatedField(queryset=OralAppeal.objects.all(), source="appeal", write_only=True)
    sent_to_id = serializers.PrimaryKeyRelatedField(
        queryset=Sender.objects.all(), source="sent_to", write_only=True, required=False, allow_null=True
    )

    class Meta:
        model = AppealForwarding
        fields = [
            "id", "appeal_id", "sent_date", "sent_to", "sent_to_id",
            "reply_number", "reply_date", "reply_received_date", "note", "created_at",
        ]
        read_only_fields = ["created_at"]

    def validate(self, attrs):
        sent = attrs.get("sent_date", getattr(self.instance, "sent_date", None))
        received = attrs.get("reply_received_date", getattr(self.instance, "reply_received_date", None))
        if sent and received and received < sent:
            raise serializers.ValidationError({"reply_received_date": "Javob xati kelgan sana yuborilgan sanadan oldin bo'lishi mumkin emas."})
        return attrs


def _fk(model, source):
    return serializers.PrimaryKeyRelatedField(
        queryset=model.objects.all(), source=source, write_only=True, required=False, allow_null=True
    )


class OralAppealSerializer(serializers.ModelSerializer):
    question = AppealQuestionSerializer(read_only=True)
    appeal_form = AppealFormSerializer(read_only=True)
    appeal_kind = AppealKindSerializer(read_only=True)
    reception_type = ReceptionTypeSerializer(read_only=True)
    signer = SignerSerializer(read_only=True)
    extended_by = SignerSerializer(read_only=True)
    department = _DepartmentShortSerializer(read_only=True)
    closed_by_name = serializers.SerializerMethodField()
    forwardings = AppealForwardingSerializer(many=True, read_only=True)

    question_id = _fk(AppealQuestion, "question")
    appeal_form_id = _fk(AppealForm, "appeal_form")
    appeal_kind_id = _fk(AppealKind, "appeal_kind")
    reception_type_id = _fk(ReceptionType, "reception_type")
    signer_id = _fk(Signer, "signer")
    department_id = _fk(Department, "department")

    # Bog'langan oxirgi topshiriq bo'yicha (views.py da annotatsiya qilinadi)
    task_id = serializers.IntegerField(read_only=True, default=None)
    task_status = serializers.CharField(read_only=True, default=None)
    task_due_date = serializers.DateField(read_only=True, default=None)
    is_overdue = serializers.SerializerMethodField()

    class Meta:
        model = OralAppeal
        fields = [
            "id", "reg_number", "reg_year",
            "question", "question_id", "applicant_type", "applicant_name", "address", "phone",
            "received_date", "appeal_form", "appeal_form_id", "reception_type", "reception_type_id",
            "appeal_kind", "appeal_kind_id", "summary", "signer", "signer_id", "department", "department_id",
            "original_due_date", "extended_due_date", "extended_by", "extended_at",
            "result_summary", "closed_by_name", "closed_at",
            "forwardings", "task_id", "task_status", "task_due_date", "is_overdue",
            "user", "created_at", "updated_at",
        ]
        read_only_fields = [
            "reg_number", "reg_year", "original_due_date", "extended_due_date", "extended_at",
            "closed_at", "user", "created_at", "updated_at",
        ]

    def get_closed_by_name(self, obj):
        user = obj.closed_by
        if not user:
            return None
        return " ".join(filter(None, [user.last_name, user.first_name])) or user.username

    def get_is_overdue(self, obj):
        """Murojaatni ko'rib chiqish muddati buzilganligi belgisi (saqlanmaydi, hisoblanadi)."""
        status = getattr(obj, "task_status", None)
        due = getattr(obj, "task_due_date", None)
        if status == "done_overdue":
            return True
        return bool(status in ACTIVE_TASK_STATUSES and due and due < timezone.localdate())

    def validate_question_id(self, question):
        # Faqat savol tanlanadi; bo'lim (ichida bandi bor yozuv) tanlanmaydi.
        # Eski murojaatdagi qiymat o'zgartirilmasa, tekshirilmaydi.
        unchanged = self.instance is not None and self.instance.question_id == getattr(question, "pk", None)
        if question is not None and not unchanged and question.children.exists():
            raise serializers.ValidationError("Bu bo'lim. Uning ichidagi aniq savolni tanlang.")
        return question

    def validate_received_date(self, value):
        if value and value > timezone.localdate():
            raise serializers.ValidationError("Kelib tushgan sana kelajakda bo'lishi mumkin emas.")
        return value


class AppealExtendSerializer(serializers.Serializer):
    """Muddatni uzaytirish: yangi muddat va kim tomonidan."""

    new_due_date = serializers.DateField()
    extended_by_id = serializers.PrimaryKeyRelatedField(queryset=Signer.objects.all(), source="extended_by")

    def validate_new_due_date(self, value):
        if value < timezone.localdate():
            raise serializers.ValidationError("Yangi muddat bugundan oldin bo'lishi mumkin emas.")
        return value


class AppealShortSerializer(serializers.ModelSerializer):
    """Topshiriq ichida ko'rsatish uchun ixcham ko'rinish."""

    question = AppealQuestionSerializer(read_only=True)
    appeal_form = AppealFormSerializer(read_only=True)
    appeal_kind = AppealKindSerializer(read_only=True)
    reception_type = ReceptionTypeSerializer(read_only=True)
    signer = SignerSerializer(read_only=True)
    department = _DepartmentShortSerializer(read_only=True)

    class Meta:
        model = OralAppeal
        fields = [
            "id", "reg_number", "question", "applicant_type", "applicant_name", "address", "phone",
            "received_date", "appeal_form", "reception_type", "appeal_kind", "summary", "signer",
            "department", "original_due_date", "extended_due_date",
        ]
