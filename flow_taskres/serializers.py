from rest_framework import serializers
from .models import TaskResponse, TaskResponseFile

class TaskResponseFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskResponseFile
        fields = ['id', 'file', 'extension', 'uploaded_at']

class TaskResponseSerializer(serializers.ModelSerializer):
    files = TaskResponseFileSerializer(many=True, read_only=True)
    uploaded_files = serializers.ListField(
        child=serializers.FileField(allow_empty_file=False, use_url=False),
        write_only=True,
        required=False
    )
    user_full_name = serializers.ReadOnlyField(source='user.get_full_name')

    class Meta:
        model = TaskResponse
        fields = [
            'id', 'task', 'user', 'user_full_name', 
            'description', 'files', 'uploaded_files', 'created_at'
        ]
        read_only_fields = ['user', 'task']

    def create(self, validated_data):
        uploaded_files = validated_data.pop('uploaded_files', [])
        response = TaskResponse.objects.create(**validated_data)
        
        for file in uploaded_files:
            TaskResponseFile.objects.create(response=response, file=file)
        
        return response

    # MANA SHU QISM QO'SHILDI:
    def update(self, instance, validated_data):
        # 1. Yangi fayllarni ajratib olish
        uploaded_files = validated_data.pop('uploaded_files', [])
        
        # 2. Asosiy maydonlarni (description) yangilash
        instance.description = validated_data.get('description', instance.description)
        instance.save()
        
        # 3. Yangi fayllarni mavjudlariga qo'shish
        for file in uploaded_files:
            TaskResponseFile.objects.create(response=instance, file=file)
            
        return instance