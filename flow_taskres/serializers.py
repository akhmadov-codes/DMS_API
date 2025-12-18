from rest_framework import serializers
from .models import TaskResponse, TaskResponseFile

class TaskResponseFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskResponseFile
        fields = ['id', 'file', 'extension', 'uploaded_at']

class TaskResponseSerializer(serializers.ModelSerializer):
    files = TaskResponseFileSerializer(many=True, read_only=True)

    uploaded_files = serializers.ListField(
        child=serializers.FileField(),
        write_only=True,
        required=False
    )

    class Meta:
        model = TaskResponse
        fields = ['description', 'files', 'uploaded_files']
        # ❌ 'user' va 'task' frontend’dan kelmaydi
