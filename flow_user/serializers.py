from rest_framework import serializers
from django.contrib.auth.models import Group
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import CustomUser, Department

class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = [ 'id', 'name' ]


class CustomUserSerializer(serializers.ModelSerializer):
    groups = serializers.SlugRelatedField(
        many=True,
        slug_field='name',
        read_only=True
    )
    department = DepartmentSerializer(read_only=True)
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'groups', 'father_name', 'last_name', 'first_name', 'email', 'department', 'position']


class UserProfileSerializer(serializers.ModelSerializer):
    groups = serializers.SlugRelatedField(
        many=True,
        slug_field='name', 
        read_only=True  
    )
    department = DepartmentSerializer(read_only=True)
    class Meta:
        model = CustomUser
        fields = ['id', 'groups', 'username', 'father_name', 'last_name', 'first_name', 'email', 'department', 'position']


class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        data["user_id"] = self.user.id
        return data