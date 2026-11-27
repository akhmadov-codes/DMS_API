from django.db import transaction
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema
from rest_framework import filters, pagination, status, viewsets
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from flow_user.permissions import IsManagerOrReadOnly

from .models import (
    Attachment,
    DeliveryType,
    DocumentType,
    IncomingDocument,
    Journal,
    Sender,
    Signer,
)
from .serializers import (
    AttachmentSerializer,
    DeliveryTypeSerializer,
    DocumentTypeSerializer,
    IncomingDocumentSerializer,
    JournalSerializer,
    SenderSerializer,
    SignerSerializer,
)


# ==============================
# Signer (imzolovchi)
# ==============================
class SignercollectionViews(APIView):
    permission_classes = [IsManagerOrReadOnly]

    def get(self, request):
        serializer = SignerSerializer(Signer.objects.all(), many=True)
        return Response({"result": serializer.data}, status=status.HTTP_200_OK)

    @swagger_auto_schema(request_body=SignerSerializer)
    def post(self, request):
        serializer = SignerSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"result": serializer.data}, status=status.HTTP_201_CREATED)
        return Response({"result": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


class SignerinstanceViews(APIView):
    permission_classes = [IsManagerOrReadOnly]

    def get(self, request, id):
        signer = get_object_or_404(Signer, id=id)
        return Response({"result": SignerSerializer(signer).data}, status=status.HTTP_200_OK)

    def _update(self, request, id, partial):
        signer = get_object_or_404(Signer, id=id)
        serializer = SignerSerializer(signer, data=request.data, partial=partial)
        if serializer.is_valid():
            serializer.save()
            return Response({"result": serializer.data}, status=status.HTTP_200_OK)
        return Response({"result": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(request_body=SignerSerializer)
    def put(self, request, id):
        return self._update(request, id, partial=False)

    @swagger_auto_schema(request_body=SignerSerializer)
    def patch(self, request, id):
        return self._update(request, id, partial=True)

    def delete(self, request, id):
        get_object_or_404(Signer, id=id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ==============================
# Ma'lumotnomalar
# ==============================
class DocumentTypeViewSet(viewsets.ModelViewSet):
    queryset = DocumentType.objects.all()
    serializer_class = DocumentTypeSerializer
    permission_classes = [IsManagerOrReadOnly]


class DeliveryTypeViewSet(viewsets.ModelViewSet):
    queryset = DeliveryType.objects.all()
    serializer_class = DeliveryTypeSerializer
    permission_classes = [IsManagerOrReadOnly]


class JournalViewSet(viewsets.ModelViewSet):
    queryset = Journal.objects.all()
    serializer_class = JournalSerializer
    permission_classes = [IsManagerOrReadOnly]


class SenderViewSet(viewsets.ModelViewSet):
    queryset = Sender.objects.all()
    serializer_class = SenderSerializer
    permission_classes = [IsManagerOrReadOnly]


# ==============================
# Kiruvchi hujjatlar
# ==============================
class IncomingDocumentPagination(pagination.PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


class IncomingDocumentViewSet(viewsets.ModelViewSet):
    serializer_class = IncomingDocumentSerializer
    permission_classes = [IsManagerOrReadOnly]
    pagination_class = IncomingDocumentPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = {
        "status": ["exact"],
        "delivery_type": ["exact"],
        "document_type": ["exact"],
        "journal": ["exact"],
        "sender": ["exact"],
        "in_number": ["exact", "icontains"],
        "out_number": ["exact", "icontains"],
    }
    search_fields = [
        "in_number",
        "out_number",
        "title",
        "signer_type__last_name",
        "signer_type__first_name",
    ]

    def get_queryset(self):
        return (
            IncomingDocument.objects.select_related(
                "delivery_type",
                "document_type",
                "journal",
                "sender",
                "signer_type",
                "user",
            )
            .prefetch_related("attachments")
            .order_by("-created_at")
        )

    def perform_create(self, serializer):
        # Muallif va boshlang'ich status avtomatik
        serializer.save(user=self.request.user, status=IncomingDocument.STATUS_DRAFT)


# ==============================
# Hujjat ilovalari (fayllar)
# ==============================
class AttachmentViewSet(viewsets.ModelViewSet):
    queryset = Attachment.objects.all()
    serializer_class = AttachmentSerializer
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsManagerOrReadOnly]

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        document_id = request.data.get("document_id")
        if not document_id:
            return Response(
                {"detail": "document_id field is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        document = get_object_or_404(IncomingDocument, id=document_id)
        files = request.FILES.getlist("files") or request.FILES.getlist("file")
        if not files:
            return Response(
                {"detail": "At least one file must be uploaded"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # bulk_create model.save() ni chaqirmaydi, shuning uchun kengaytmani shu yerda hisoblaymiz
        created_attachments = Attachment.objects.bulk_create(
            [
                Attachment(document=document, file=f, extension=Attachment.extension_of(f.name))
                for f in files
            ]
        )

        if document.status == IncomingDocument.STATUS_DRAFT:
            document.status = IncomingDocument.STATUS_ATTACHED
            document.save(update_fields=["status"])

        serializer = self.get_serializer(created_attachments, many=True)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        attachment = self.get_object()
        document = attachment.document
        response = super().destroy(request, *args, **kwargs)
        # Oxirgi fayl o'chsa hujjat qoralama holatiga qaytadi
        if not document.attachments.exists():
            document.status = IncomingDocument.STATUS_DRAFT
            document.save(update_fields=["status"])
        return response
