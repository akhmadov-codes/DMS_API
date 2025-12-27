from django.shortcuts import get_object_or_404
from django.db import transaction
from rest_framework import viewsets, permissions, pagination, status, filters
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from .models import (
    DeliveryType, DocumentType, Journal, 
    Sender, IncomingDocument, Attachment
)
from .serializers import (
    DeliveryTypeSerializer, JournalSerializer, SenderSerializer,
    IncomingDocumentSerializer, AttachmentSerializer, DocumentTypeSerializer
)

# ==============================
# Pagination (O'zgarishsiz qoldi)
# ==============================
class IncomingDocumentPagination(pagination.PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

# ==============================
# Lookup ViewSets (Kodni qisqartirdik)
# ==============================
class DocumentTypeViewSet(viewsets.ModelViewSet):
    queryset = DocumentType.objects.all()
    serializer_class = DocumentTypeSerializer
    permission_classes = [permissions.IsAuthenticated]

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
# IncomingDocument CRUD (Optimallashgan)
# ==============================
class IncomingDocumentViewSet(viewsets.ModelViewSet):
    serializer_class = IncomingDocumentSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = IncomingDocumentPagination
    
    # DjangoFilterBackend Vue'dan keladigan filtrlarni avtomatik boshqaradi
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = {
        'status': ['exact'],
        'delivery_type': ['exact'],
        'document_type': ['exact'],
        'journal': ['exact'],
        'sender': ['exact'],
        'in_number': ['exact', 'icontains'], # Vue yuborayotgan filtrlar uchun
        'out_number': ['exact', 'icontains'],
    }
    search_fields = ['in_number', 'out_number', 'title', 'signer']

    def get_queryset(self):
        """
        N+1 muammosini hal qilish uchun select_related va prefetch_related qo'shildi.
        Bu Vue'dagi ro'yxatni yuklash tezligini bir necha barobar oshiradi.
        """
        return IncomingDocument.objects.select_related(
            'delivery_type', 'document_type', 'journal', 'sender', 'user'
        ).prefetch_related('attachments').all().order_by('-created_at')

    def perform_create(self, serializer):
        """
        Vue'dan kelgan ma'lumotlarni serializer orqali validatsiya qilib saqlaydi.
        User va Status avtomatik biriktiriladi.
        """
        serializer.save(user=self.request.user, status=IncomingDocument.STATUS_DRAFT)

    def perform_update(self, serializer):
        """
        Update paytida status o'zgarmasligini ta'minlaydi (Vue logikasi bo'yicha).
        """
        serializer.save()

# ==============================
# Attachment CRUD (Optimallashgan)
# ==============================
class AttachmentViewSet(viewsets.ModelViewSet):
    queryset = Attachment.objects.all()
    serializer_class = AttachmentSerializer
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic # Ma'lumotlar butunligini ta'minlash uchun
    def create(self, request, *args, **kwargs):
        document_id = request.data.get('document_id')
        if not document_id:
            return Response({"detail": "document_id field is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        document = get_object_or_404(IncomingDocument, id=document_id)
        files = request.FILES.getlist('files') or request.FILES.getlist('file')

        if not files:
            return Response({"detail": "At least one file must be uploaded"}, status=status.HTTP_400_BAD_REQUEST)

        # Bulk create: Har bir fayl uchun alohida so'rov o'rniga bitta so'rovda saqlash
        attachments_to_create = [
            Attachment(document=document, file=f) for f in files
        ]
        created_attachments = Attachment.objects.bulk_create(attachments_to_create)

        # Statusni yangilash
        if document.status == IncomingDocument.STATUS_DRAFT:
            document.status = IncomingDocument.STATUS_ATTACHED
            document.save(update_fields=['status'])

        # Vue kutgan formatdagi javobni qaytarish
        serializer = self.get_serializer(created_attachments, many=True)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        attachment = self.get_object()
        document = attachment.document
        
        response = super().destroy(request, *args, **kwargs)

        # Agar bu oxirgi fayl bo'lsa, statusni qaytaramiz
        if not document.attachments.exists():
            document.status = IncomingDocument.STATUS_DRAFT
            document.save(update_fields=['status'])

        return response