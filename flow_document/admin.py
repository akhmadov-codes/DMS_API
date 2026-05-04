from django.contrib import admin
from .models import IncomingDocument, Attachment, Journal, DeliveryType, Sender, DocumentType, Signer
# Register your models here.

admin.site.register([IncomingDocument, DocumentType, Attachment, Journal, DeliveryType, Sender, Signer])