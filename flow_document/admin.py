from django.contrib import admin
from .models import IncomingDocument, Attachment, Journal, DeliveryType, Sender, DocumentType
# Register your models here.

admin.site.register([IncomingDocument, DocumentType, Attachment, Journal, DeliveryType, Sender])