from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TaskResponseViewSet, TaskResponseFileViewSet

router = DefaultRouter()
router.register(r'task-responses', TaskResponseViewSet, basename='task-responses')
router.register(r'task-response-files', TaskResponseFileViewSet, basename='task-response-files')

urlpatterns = [
    path('', include(router.urls)),
]
