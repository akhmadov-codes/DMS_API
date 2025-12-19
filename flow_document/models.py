from django.db import models
from flow_user.models import CustomUser
import os

# ==== Lookup / Directory Models ====
class DeliveryType(models.Model):
    name = models.CharField(max_length=255, unique=True)
    def __str__(self):
        return self.name
    
class DocumentType(models.Model):
    name = models.CharField(max_length=255, unique=True)
    def __str__(self):
        return self.name


class Journal(models.Model):
    name = models.TextField(unique=True)
    def __str__(self):
        return self.name[:50]


class Sender(models.Model):
    name = models.CharField(max_length=255, unique=True)
    def __str__(self):
        return self.name


# ==== Main Document Model ====
class IncomingDocument(models.Model):
    STATUS_DRAFT = 'draft'
    STATUS_ATTACHED = 'attached'

    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Draft'),
        (STATUS_ATTACHED, 'Attached'),
    ]

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="documents"
    )
    in_number = models.CharField(max_length=50, blank=True, null=True)
    out_number = models.CharField(max_length=50, blank=True, null=True)
    delivery_type = models.ForeignKey(
        DeliveryType,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="documents"
    )
    document_type = models.ForeignKey(
        DocumentType,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="documents"
    )
    signer = models.CharField(max_length=255, blank=True, null=True)
    journal = models.ForeignKey(
        Journal,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="documents"
    )
    title = models.TextField()
    sender = models.ForeignKey(
        Sender,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="documents"
    )
    summary = models.TextField(blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.id} - {self.title[:50]}"


# ==== Attachment Model ====
class Attachment(models.Model):
    document = models.ForeignKey(
        IncomingDocument,
        on_delete=models.CASCADE,
        related_name="attachments"
    )
    file = models.FileField(upload_to="attachments/")
    extension = models.CharField(max_length=10, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.file and not self.extension:
            _, ext = os.path.splitext(self.file.name)
            self.extension = ext.lower().lstrip('.')
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.file.name} (doc #{self.document_id})"
