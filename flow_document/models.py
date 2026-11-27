import os
from django.db import models
from django.utils import timezone

from flow_user.models import CustomUser


# 1. Fayllarni yillar/oylar bo'yicha tartiblash
def attachment_path(instance, filename):
    now = timezone.now()
    return f"attachments/{now.year}/{now.month}/{filename}"

class Signer(models.Model):
    last_name = models.CharField(max_length=255, blank=True, null=True)
    first_name = models.CharField(max_length=255, blank=True, null=True)
    @property
    def short_name(self):
        return f'{(self.last_name or "")[:1]}.{self.first_name or ""}'

    def __str__(self):
        return self.short_name

class DeliveryType(models.Model):
    name = models.CharField(max_length=255, unique=True)
    def __str__(self):
        return self.name

class DocumentType(models.Model):
    name = models.CharField(max_length=255, unique=True)
    def __str__(self):
        return self.name

class Journal(models.Model):
    name = models.CharField(max_length=500, unique=True)
    def __str__(self):
        return self.name[:50]

class Sender(models.Model):
    name = models.CharField(max_length=255, unique=True)
    def __str__(self):
        return self.name


class IncomingDocument(models.Model):
    STATUS_DRAFT = "draft"
    STATUS_ATTACHED = "attached"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_ATTACHED, "Attached"),
    ]
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="documents")
    in_number = models.CharField(max_length=50, blank=True, null=True, db_index=True)
    reg_number = models.CharField(blank=True, null=True, db_index=True)
    reg_data = models.DateField(null=True, blank=True)
    in_date = models.DateField(blank=True, null=True, db_index=True)
    out_number = models.CharField(max_length=50, blank=True, null=True, db_index=True)
    delivery_type = models.ForeignKey(DeliveryType, on_delete=models.SET_NULL, blank=True, null=True, related_name="documents",)
    document_type = models.ForeignKey(DocumentType, on_delete=models.SET_NULL, blank=True, null=True, related_name="documents",)
    signer_type = models.ForeignKey(Signer, on_delete=models.SET_NULL, null=True, blank=True, related_name="documents")
    journal = models.ForeignKey(Journal, on_delete=models.SET_NULL, blank=True, null=True, related_name="documents",)
    title = models.TextField()
    sender = models.ForeignKey(Sender, on_delete=models.SET_NULL, blank=True, null=True, related_name="documents",)
    summary = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
    def __str__(self):
        return f"{self.id} - {self.title[:50]}"


class Attachment(models.Model):
    document = models.ForeignKey(
        IncomingDocument, on_delete=models.CASCADE, related_name="attachments"
    )
    file = models.FileField(upload_to=attachment_path)
    extension = models.CharField(max_length=10, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @staticmethod
    def extension_of(filename):
        _, ext = os.path.splitext(filename or "")
        return ext.lower().lstrip(".")[:10]

    def save(self, *args, **kwargs):
        if self.file and not self.extension:
            self.extension = self.extension_of(self.file.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.file.name} (doc #{self.document_id})"
