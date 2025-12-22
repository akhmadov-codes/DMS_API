from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TaskResponseViewSet, TaskResponseFileDeleteView  # O'zingiz yozgan viewni import qiling

# Router obyektini yaratamiz
router = DefaultRouter()

# TaskResponseViewSet-ni routerga bog'laymiz
# 'task-responses' — bu URL'ning boshlang'ich qismi bo'ladi
router.register(r'task-responses', TaskResponseViewSet, basename='task-response')

urlpatterns = [
    # Routerdagi barcha URL-larni urlpatterns-ga qo'shamiz
    path('', include(router.urls)),
    path('task-response-files/<int:pk>/', TaskResponseFileDeleteView.as_view(), name='delete-file'),
]