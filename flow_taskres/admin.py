from django.contrib import admin
from .models import TaskResponse, TaskResponseFile
# Register your models here.


admin.site.register([ TaskResponse, TaskResponseFile ])