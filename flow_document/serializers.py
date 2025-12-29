from rest_framework import serializers
from .models import DeliveryType, DocumentType, Journal, Sender, IncomingDocument, Attachment
import os

# ==== Lookup Models ==== 
# Bu yerda o'zgarishsiz qoldirdik, chunki ular oddiy
class DeliveryTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryType
        fields = ['id', 'name']
class DocumentTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentType
        fields = ['id', 'name']
class JournalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Journal
        fields = ['id', 'name']
class SenderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sender
        fields = ['id', 'name']
# ==== Attachment Serializer ====
class AttachmentSerializer(serializers.ModelSerializer):
    document_id = serializers.PrimaryKeyRelatedField(
        queryset=IncomingDocument.objects.all(),
        write_only=True,
        source='document'
    )
    class Meta:
        model = Attachment
        fields = ['id', 'document_id', 'file', 'extension', 'created_at']
        read_only_fields = ['created_at', 'extension']
    def to_representation(self, instance):
        """
        Agar bulk_create sababli bazada extension bo'sh qolgan bo'lsa,
        uni foydalanuvchiga yuborishdan oldin aniqlab beradi.
        """
        ret = super().to_representation(instance)
        # Agar extension bo'sh bo'lsa, fayl nomidan olamiz
        if not ret.get('extension') and instance.file:
            _, ext = os.path.splitext(instance.file.name)
            ret['extension'] = ext.lower().lstrip('.')
        return ret


class IncomingDocumentSerializer(serializers.ModelSerializer):
    # 1. READ-ONLY: Ro'yxatda va Tahrirlashda Vue obyekt ichidan .name ni o'qishi uchun
    delivery_type = DeliveryTypeSerializer(read_only=True)
    document_type = DocumentTypeSerializer(read_only=True)
    journal = JournalSerializer(read_only=True)
    sender = SenderSerializer(read_only=True)
    attachments = AttachmentSerializer(many=True, read_only=True)
    # 2. WRITE-ONLY: Vue handleSubmit yuborgan ID larni qabul qilish uchun
    # source='...' qismi bu ID larni modeldagi ForeignKey maydonlariga bog'laydi
    delivery_type_id = serializers.PrimaryKeyRelatedField(
        queryset=DeliveryType.objects.all(), source='delivery_type', write_only=True, required=False, allow_null=True
    )
    document_type_id = serializers.PrimaryKeyRelatedField(
        queryset=DocumentType.objects.all(), source='document_type', write_only=True, required=False, allow_null=True
    )
    journal_id = serializers.PrimaryKeyRelatedField(
        queryset=Journal.objects.all(), source='journal', write_only=True, required=False, allow_null=True
    )
    sender_id = serializers.PrimaryKeyRelatedField(
        queryset=Sender.objects.all(), source='sender', write_only=True, required=False, allow_null=True
    )
    class Meta:
        model = IncomingDocument
        fields = [
            'id', 'user', 'in_number', 'in_date', 'out_number', 'delivery_type', 'delivery_type_id', 'document_type', 'document_type_id',
            'journal', 'journal_id', 'sender', 'sender_id', 'signer', 'title', 'summary', 'status', 'attachments', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'status', 'user']
    def to_representation(self, instance):
        """
        Vue tahrirlash (Edit) oynasini ochganda `props.selectedFile.delivery_type.id` 
        kabi kodlar xato bermasligi uchun null qiymatlarni bo'sh obyektga aylantiradi.
        """
        ret = super().to_representation(instance)
        fields_to_fix = ['delivery_type', 'document_type', 'journal', 'sender']
        for field in fields_to_fix:
            if ret.get(field) is None:
                ret[field] = {'id': None, 'name': ""}
        return ret