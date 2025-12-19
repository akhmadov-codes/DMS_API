from rest_framework import serializers
from .models import TaskResponse, TaskResponseFile

# -------------------------------
# TaskResponseFileSerializer
# -------------------------------
class TaskResponseFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskResponseFile
        fields = ['id', 'file', 'extension', 'uploaded_at']
        read_only_fields = ['id', 'extension', 'uploaded_at']


# -------------------------------
# TaskResponseSerializer
# -------------------------------
class TaskResponseSerializer(serializers.ModelSerializer):
    files = TaskResponseFileSerializer(many=True, read_only=True)

    class Meta:
        model = TaskResponse
        fields = ['id', 'task', 'user', 'description', 'files', 'created_at']
        read_only_fields = ['id', 'task', 'user', 'files', 'created_at']
