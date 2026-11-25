from django.db import transaction
from rest_framework import serializers

from flow_document.serializers import IncomingDocumentSerializer
from flow_taskres.serializers import TaskResponseSerializer
from flow_user.models import CustomUser
from flow_user.serializers import TaskAssigneeSerializer

from .models import IncomingDocument, Subject, Task, TaskAssignee, TaskDescription

ALL_USERS = "all-users"


class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = '__all__'


class TaskDescriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskDescription
        fields = '__all__'


class TaskSerializer(serializers.ModelSerializer):
    assignees = serializers.SerializerMethodField()
    document = IncomingDocumentSerializer(read_only=True)
    subject = SubjectSerializer(read_only=True)
    task_description = TaskDescriptionSerializer(read_only=True)
    responses = TaskResponseSerializer(many=True, read_only=True)
    document_id = serializers.PrimaryKeyRelatedField(queryset=IncomingDocument.objects.all(), write_only=True, source='document')
    subject_id = serializers.PrimaryKeyRelatedField(queryset=Subject.objects.all(), write_only=True, source='subject')
    task_description_id = serializers.PrimaryKeyRelatedField(queryset=TaskDescription.objects.all(), write_only=True, source='task_description')
    # ID'lar ro'yxati yoki ["all-users"] (barcha faol foydalanuvchilar)
    assignees_ids = serializers.ListField(child=serializers.CharField(), write_only=True, required=False)

    class Meta:
        model = Task
        fields = [
            'id', 'document', 'responses', 'document_id', 'subject', 'subject_id', 'description', 'task_description_id', 'task_description',
            'due_date', 'assignees', 'assignees_ids', 'status',
            'created_at', 'updated_at'
        ]

    def get_assignees(self, obj):
        # TaskViewSet.get_queryset() da "taskassignee_set" user va bo'limi bilan oldindan yuklanadi,
        # shuning uchun bu yerda qo'shimcha so'rov ketmaydi.
        links = sorted(obj.taskassignee_set.all(), key=lambda a: a.order)
        return [
            {
                "task_assignee_id": link.id,
                "order": link.order,
                **TaskAssigneeSerializer(link.user).data,
            }
            for link in links
        ]

    def validate_assignees_ids(self, value):
        if ALL_USERS in value:
            return [ALL_USERS]
        user_ids = []
        for raw in value:
            try:
                user_id = int(raw)
            except (TypeError, ValueError):
                raise serializers.ValidationError(f"Noto'g'ri foydalanuvchi ID: {raw}")
            if user_id not in user_ids:  # takrorlarni olib tashlaymiz, tartib saqlanadi
                user_ids.append(user_id)
        existing = set(CustomUser.objects.filter(id__in=user_ids).values_list('id', flat=True))
        missing = [uid for uid in user_ids if uid not in existing]
        if missing:
            raise serializers.ValidationError(f"Foydalanuvchi topilmadi: {missing}")
        return user_ids

    @staticmethod
    def _set_assignees(task, assignee_ids):
        if ALL_USERS in assignee_ids:
            user_ids = CustomUser.objects.filter(is_active=True).values_list('id', flat=True)
        else:
            user_ids = assignee_ids
        TaskAssignee.objects.bulk_create(
            [TaskAssignee(task=task, user_id=uid, order=index) for index, uid in enumerate(user_ids, start=1)]
        )

    def create(self, validated_data):
        assignee_ids = validated_data.pop('assignees_ids', [])
        with transaction.atomic():
            task = Task.objects.create(**validated_data)
            if assignee_ids:
                self._set_assignees(task, assignee_ids)
        return task

    def update(self, instance, validated_data):
        assignee_ids = validated_data.pop('assignees_ids', None)
        with transaction.atomic():
            instance = super().update(instance, validated_data)
            if assignee_ids is not None:
                TaskAssignee.objects.filter(task=instance).delete()
                if assignee_ids:
                    self._set_assignees(instance, assignee_ids)
        # Prefetch keshi eskirgan bo'lishi mumkin - javob yangi ma'lumotdan qurilsin
        if hasattr(instance, '_prefetched_objects_cache'):
            instance._prefetched_objects_cache = {}
        return instance
