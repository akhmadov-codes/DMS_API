from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import CustomUser, Department
from django.contrib.auth.models import Group

class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = [ 'id', 'name', 'created_at' ]
class TaskAssigneeSerializer(serializers.ModelSerializer):
    department_name = serializers.ReadOnlyField(source='department.name')
    class Meta:
        model = CustomUser
        fields = ['id', 'last_name', 'first_name', 'father_name', 'department_name']

class CustomUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        required=True,
        min_length=8
    )
    groups = serializers.SlugRelatedField(
        many=True,
        slug_field='name',
        read_only=True
    )
    department = DepartmentSerializer(read_only=True)
    department_id = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.all(),
        source='department',
        write_only=True
    )
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'is_rector', 'groups', 'father_name', 'last_name', 'first_name', 'email', 'department', 'department_id', 'position', 'password', 'date_joined']

    def create(self, validated_data):
            password = validated_data.pop('password')
            user = CustomUser(**validated_data)
            user.set_password(password)
            user.save()
            default_group, created = Group.objects.get_or_create(name='user')
            user.groups.add(default_group)
            return user
    
    def update(self, instance, validated_data):
            password = validated_data.pop('password', None)
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            if password:
                instance.set_password(password)
            instance.save()
            return instance

class UserProfileSerializer(serializers.ModelSerializer):
    groups = serializers.SlugRelatedField(
        many=True,
        slug_field='name', 
        read_only=True  
    )
    department = DepartmentSerializer(read_only=True)
    class Meta:
        model = CustomUser
        fields = ['id', 'is_rector', 'groups', 'username', 'father_name', 'last_name', 'first_name', 'email', 'department', 'position']


class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        data["user_id"] = self.user.id
        return data