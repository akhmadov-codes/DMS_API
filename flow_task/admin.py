from django.contrib import admin
from .models import Task, Subject, TaskDescription, TaskAssignee
# Register your models here.

admin.site.register([ Task, Subject, TaskDescription, TaskAssignee ])