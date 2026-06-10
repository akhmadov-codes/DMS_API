from rest_framework import serializers
from flow_document.serializers import IncomingDocumentSerializer
from flow_taskres.serializers import TaskResponseSerializer
from flow_user.serializers import TaskAssigneeSerializer
from .models import IncomingDocument, Subject, Task, TaskDescription, TaskAssignee
from flow_user.models import CustomUser

class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = '__all__'

class TaskDescriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskDescription
        fields = '__all__'

class TaskSerializer(serializers.ModelSerializer):
    document = IncomingDocumentSerializer(read_only=True)
    subject = SubjectSerializer(read_only=True)
    task_description = TaskDescriptionSerializer(read_only=True)
    assignees = TaskAssigneeSerializer(many=True, read_only=True)
    responses = TaskResponseSerializer(many=True, read_only=True)
    document_id = serializers.PrimaryKeyRelatedField(queryset=IncomingDocument.objects.all(), write_only=True, source='document')
    subject_id = serializers.PrimaryKeyRelatedField(queryset=Subject.objects.all(), write_only=True, source='subject')
    task_description_id = serializers.PrimaryKeyRelatedField(queryset=TaskDescription.objects.all(), write_only=True, source='task_description')
    assignees_ids = serializers.ListField(child=serializers.CharField(), write_only=True, required=False)

    class Meta:
        model = Task
        fields = [
            'id', 'document', 'responses', 'document_id', 'subject', 'subject_id', 'description', 'task_description_id', 'task_description',
            'due_date', 'assignees', 'assignees_ids', 'status',
            'created_at', 'updated_at'
        ]

    def create(self, validated_data):
        assignee_ids = validated_data.pop('assignees_ids', [])
        task = Task.objects.create(**validated_data)
        if "all-users" in assignee_ids:
            users = CustomUser.objects.filter(is_active=True)
            for index, user in enumerate(users):
                TaskAssignee.objects.create(
                    task=task, 
                    user=user, 
                    order=index + 1 
                )
        elif assignee_ids:
            for index, user_id in enumerate(assignee_ids):
                TaskAssignee.objects.create(
                    task=task, 
                    user_id=int(user_id), 
                    order=index + 1
                )
                
        return task

    def update(self, instance, validated_data):
        assignee_ids = validated_data.pop('assignees_ids', None)
        instance = super().update(instance, validated_data)
        if assignee_ids is not None:
            TaskAssignee.objects.filter(task=instance).delete()
            
            if "all-users" in assignee_ids:
                users = CustomUser.objects.filter(is_active=True)
                for index, user in enumerate(users):
                    TaskAssignee.objects.create(
                        task=instance, 
                        user=user, 
                        order=index + 1
                    )
            elif assignee_ids:
                for index, user_id in enumerate(assignee_ids):
                    TaskAssignee.objects.create(
                        task=instance, 
                        user_id=int(user_id), 
                        order=index + 1
                    )
                    
        return instance
