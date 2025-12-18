from django.urls import path
from .views import TaskResponseViewSet

task_response_list = TaskResponseViewSet.as_view({
    'get': 'list',
    'post': 'create'
})

urlpatterns = [
    path('task-responses/<int:task_id>/responses/', task_response_list, name='task-responses'),
]
