from django.conf import settings
from django.db import models


class ProcessModel(models.Model):
    file_name = models.CharField(max_length=256)
    hash = models.CharField(max_length=256, blank=True)
    upload_date = models.DateTimeField(auto_now_add=True, blank=True)
    executable = models.BooleanField(default=False)
    media = models.FileField(null=True, blank=True)
    name = models.CharField(max_length=256)


class SbpmActor(models.Model):
    display_name = models.CharField(max_length=256)
    name = models.CharField(max_length=256)
    process_model = models.ForeignKey(ProcessModel, on_delete=models.CASCADE)
    is_start_actor = models.BooleanField(default=False)
    executed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)


class ProcessInstance(models.Model):
    name = models.CharField(max_length=128)
    model = models.ForeignKey(ProcessModel, on_delete=models.CASCADE)
    state = models.IntegerField(blank=True)