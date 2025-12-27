from rest_framework import serializers
from django.db import transaction
from .models import TaskResponse, TaskResponseFile

class TaskResponseFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskResponseFile
        fields = ['id', 'file', 'extension', 'uploaded_at']

class TaskResponseSerializer(serializers.ModelSerializer):
    files = TaskResponseFileSerializer(many=True, read_only=True)
    uploaded_files = serializers.ListField(
        child=serializers.FileField(allow_empty_file=False),
        write_only=True, required=False
    )
    user_full_name = serializers.ReadOnlyField(source='user.get_full_name')

    class Meta:
        model = TaskResponse
        fields = ['id', 'task', 'user', 'user_full_name', 'description', 'files', 'uploaded_files', 'created_at']
        read_only_fields = ['user']

    def validate(self, attrs):
        request = self.context.get('request')
        task = attrs.get('task')
        # Faqat vazifaga biriktirilganlar yoki admin javob yoza oladi
        if task and request and not request.user.groups.filter(name__in=['admin', 'devonxona']).exists():
            if not task.assignees.filter(id=request.user.id).exists():
                raise serializers.ValidationError("Siz ushbu vazifaga biriktirilmagansiz!")
        return attrs

    def create(self, validated_data):
        uploaded_files = validated_data.pop('uploaded_files', [])
        with transaction.atomic():
            response = TaskResponse.objects.create(**validated_data)
            if uploaded_files:
                # bulk_create o'rniga har bir faylni alohida create qilamiz
                # Bu modeldagi save() metodini (va extension mantiqini) ishga tushiradi
                for file in uploaded_files:
                    TaskResponseFile.objects.create(response=response, file=file)
        return response

    def update(self, instance, validated_data):
        uploaded_files = validated_data.pop('uploaded_files', [])
        with transaction.atomic():
            instance = super().update(instance, validated_data)
            if uploaded_files:
                # Tahrirlashda ham yangi fayllar uchun model save() mantiqi ishlaydi
                for file in uploaded_files:
                    TaskResponseFile.objects.create(response=instance, file=file)
        return instance