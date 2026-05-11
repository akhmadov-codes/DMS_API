from django.contrib import admin
from .models import Task, Subject, TaskDescription
# Register your models here.

admin.site.register([ Task, Subject, TaskDescription ])