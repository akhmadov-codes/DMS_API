from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TaskViewSet, SubjectViewSet, TaskdiscriptionViewSet

router = DefaultRouter()
router.register(r'subjects', SubjectViewSet, basename='subjects')
router.register(r'taskdiscriptions', TaskdiscriptionViewSet, basename='taskdiscriptions')
router.register(r'tasks', TaskViewSet, basename='tasks')

urlpatterns = [
    path('', include(router.urls)),
]
