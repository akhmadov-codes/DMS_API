from rest_framework import viewsets, response
from .models import CustomUser, Department
from .serializers import CustomUserSerializer, DepartmentSerializer
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.response import Response
from .serializers import MyTokenObtainPairSerializer, CustomUserSerializer, UserProfileSerializer
from rest_framework.views import APIView
from django.contrib.auth.models import Group

class UserPagination(PageNumberPagination):
    page_size = 150
    page_size_query_param = 'page_size'
    max_page_size = 150
class DepartmentPagination(PageNumberPagination):
    page_size = 200
    page_size_query_param = 'page_size'
    max_page_size = 200

class DepartmentViewSet(viewsets.ModelViewSet):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = DepartmentPagination

class CustomUserViewSet(viewsets.ModelViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    permission_classes = [IsAuthenticated]
    pagination_class = UserPagination
    def perform_create(self, serializer):
        # Foydalanuvchini yaratish va default "User" guruhini qo‘shish
        user = serializer.save()
        user.groups.add(Group.objects.get(name="user"))

class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)