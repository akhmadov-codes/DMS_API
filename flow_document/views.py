from rest_framework import viewsets, permissions, pagination, status
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from .models import (
    DeliveryType,
    Journal,
    Sender,
    IncomingDocument,
    Attachment
)
from .serializers import (
    DeliveryTypeSerializer,
    JournalSerializer,
    SenderSerializer,
    IncomingDocumentSerializer,
    AttachmentSerializer
)

# ==============================
# Pagination
# ==============================
class IncomingDocumentPagination(pagination.PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


# ==============================
# Lookup / Directory CRUD
# ==============================
class DeliveryTypeViewSet(viewsets.ModelViewSet):
    queryset = DeliveryType.objects.all()
    serializer_class = DeliveryTypeSerializer
    permission_classes = [permissions.IsAuthenticated]


class JournalViewSet(viewsets.ModelViewSet):
    queryset = Journal.objects.all()
    serializer_class = JournalSerializer
    permission_classes = [permissions.IsAuthenticated]


class SenderViewSet(viewsets.ModelViewSet):
    queryset = Sender.objects.all()
    serializer_class = SenderSerializer
    permission_classes = [permissions.IsAuthenticated]


# ==============================
# IncomingDocument CRUD
# ==============================
class IncomingDocumentViewSet(viewsets.ModelViewSet):
    queryset = IncomingDocument.objects.all().order_by('-created_at')
    serializer_class = IncomingDocumentSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = IncomingDocumentPagination

    def create(self, request, *args, **kwargs):
        """
        Yangi hujjat yaratish:
        - user avtomatik
        - status har doim DRAFT
        - FK lar ID orqali qabul qilinadi
        """
        data = request.data

        document = IncomingDocument.objects.create(
            user=request.user,
            in_number=data.get('in_number'),
            out_number=data.get('out_number'),
            signer=data.get('signer'),
            title=data.get('title'),
            summary=data.get('summary'),
            status=IncomingDocument.STATUS_DRAFT,

            delivery_type_id=data.get('delivery_type'),
            journal_id=data.get('journal'),
            sender_id=data.get('sender'),
        )

        serializer = self.get_serializer(document)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        """
        Hujjatni tahrirlash (PUT / PATCH):
        - status bu yerda o‘zgarmaydi
        """
        document = self.get_object()
        data = request.data

        document.in_number = data.get('in_number', document.in_number)
        document.out_number = data.get('out_number', document.out_number)
        document.signer = data.get('signer', document.signer)
        document.title = data.get('title', document.title)
        document.summary = data.get('summary', document.summary)

        if 'delivery_type' in data:
            document.delivery_type_id = data.get('delivery_type')
        if 'journal' in data:
            document.journal_id = data.get('journal')
        if 'sender' in data:
            document.sender_id = data.get('sender')

        document.save()

        serializer = self.get_serializer(document)
        return Response(serializer.data)


# ==============================
# Attachment CRUD
# ==============================
class AttachmentViewSet(viewsets.ModelViewSet):
    queryset = Attachment.objects.all().order_by('-created_at')
    serializer_class = AttachmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        """
        Bulk file upload:
        - document_id majburiy
        - files[] → bir nechta fayl yuborish mumkin
        - document status avtomatik attached bo'ladi
        """
        document_id = request.data.get('document_id')
        if not document_id:
            return Response(
                {"detail": "document_id field is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        document = get_object_or_404(IncomingDocument, id=document_id)

        files = request.FILES.getlist('files')
        if not files:
            return Response(
                {"detail": "At least one file must be uploaded"},
                status=status.HTTP_400_BAD_REQUEST
            )

        attachments = []
        for file in files:
            attachment = Attachment.objects.create(document=document, file=file)
            attachments.append(attachment)

        # Document statusini avtomatik o‘zgartirish
        if document.status == IncomingDocument.STATUS_DRAFT and attachments:
            document.status = IncomingDocument.STATUS_ATTACHED
            document.save(update_fields=['status'])

        serializer = self.get_serializer(attachments, many=True)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        """
        Attachment o‘chirilsa:
        - agar boshqa attachment qolmasa → document.status = draft
        """
        attachment = self.get_object()
        document = attachment.document

        attachment.delete()

        if not document.attachments.exists():
            document.status = IncomingDocument.STATUS_DRAFT
            document.save(update_fields=['status'])

        return Response(status=status.HTTP_204_NO_CONTENT)
