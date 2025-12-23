from rest_framework import serializers
from .models import Task, Subject, IncomingDocument
from flow_user.models import CustomUser
from flow_document.serializers import IncomingDocumentSerializer
from flow_user.serializers import CustomUserSerializer, TaskAssigneeSerializer
from flow_taskres.serializers import TaskResponseSerializer

class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = '__all__'

class TaskSerializer(serializers.ModelSerializer):
    # GET uchun nested object
    document = IncomingDocumentSerializer(read_only=True)
    subject = SubjectSerializer(read_only=True)
    assignees = TaskAssigneeSerializer(many=True, read_only=True)
    responses = TaskResponseSerializer(many=True, read_only=True)
    
    # Create/Update uchun bog'liqliklarni id orqali
    document_id = serializers.PrimaryKeyRelatedField(
        queryset=IncomingDocument.objects.all(),
        write_only=True,
        source='document'
    )
    subject_id = serializers.PrimaryKeyRelatedField(
        queryset=Subject.objects.all(),
        write_only=True,
        source='subject'
    )
    assignees_ids = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.all(),
        many=True,
        write_only=True,
        source='assignees'
    )

    class Meta:
        model = Task
        fields = [
            'id', 'document', 'responses', 'document_id', 'subject', 'subject_id', 'description', 
            'due_date', 'assignees', 'assignees_ids', 'status', 
            'created_at', 'updated_at'
        ]
