from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import CustomUser, Department
from .permissions import IsAdminOrReadOnly, IsManagerOrReadOnly
from .serializers import (
    CustomUserSerializer,
    DepartmentSerializer,
    MyTokenObtainPairSerializer,
    UserProfileSerializer,
)


class UserPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 50


class DepartmentPagination(PageNumberPagination):
    page_size = 200
    page_size_query_param = "page_size"
    max_page_size = 200


class DepartmentViewSet(viewsets.ModelViewSet):
    queryset = Department.objects.order_by("id")
    serializer_class = DepartmentSerializer
    permission_classes = [IsManagerOrReadOnly]
    pagination_class = DepartmentPagination


class CustomUserViewSet(viewsets.ModelViewSet):
    queryset = (
        CustomUser.objects.select_related("department")
        .prefetch_related("groups")
        .order_by("-id")
    )
    serializer_class = CustomUserSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    permission_classes = [IsAdminOrReadOnly]
    pagination_class = UserPagination
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    search_fields = ["first_name", "last_name"]
    # Yangi foydalanuvchiga "user" guruhi serializer.create() ichida biriktiriladi


class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)


class LogoutView(APIView):
    """
    Frontend chiqishda chaqiradi. JWT stateless bo'lgani uchun token
    klient tomonda o'chiriladi; server tomonda qiladigan ish yo'q.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        return Response(status=status.HTTP_204_NO_CONTENT)
