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
        queryset=Group.objects.all(),
        required=False,                # groups ixtiyoriy
        default=Group.objects.filter(name='User')  # agar berilmasa default "User"
    )
    department = DepartmentSerializer(read_only=True)
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'last_name', 'first_name', 'email', 'groups', 'department']


class UserProfileSerializer(serializers.ModelSerializer):
    groups = serializers.SlugRelatedField(
        many=True,             # ko‘p guruh bo‘lishi mumkin
        slug_field='name',     # shu fieldni ko‘rsatadi (id o‘rniga)
        queryset=Group.objects.all()  # serializer POST/PUT uchun kerak
    )
    department = DepartmentSerializer(read_only=True)
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'last_name', 'first_name', 'email', 'department', 'groups']

class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        data["user_id"] = self.user.id
        return data