from rest_framework import serializers
from .models import DeliveryType, DocumentType, Journal, Sender, IncomingDocument, Attachment, Signer
import os

class SignerSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    class Meta:
        model = Signer
        fields = [ 'id', 'last_name', 'first_name', 'full_name' ]
    def get_full_name(self, obj):
        return obj.short_name
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
        ret = super().to_representation(instance)
        if not ret.get('extension') and instance.file:
            _, ext = os.path.splitext(instance.file.name)
            ret['extension'] = ext.lower().lstrip('.')
        return ret


class IncomingDocumentSerializer(serializers.ModelSerializer):
    delivery_type = DeliveryTypeSerializer(read_only=True)
    document_type = DocumentTypeSerializer(read_only=True)
    journal = JournalSerializer(read_only=True)
    signer_type = SignerSerializer(read_only=True)
    sender = SenderSerializer(read_only=True)
    attachments = AttachmentSerializer(many=True, read_only=True)
    delivery_type_id = serializers.PrimaryKeyRelatedField( queryset=DeliveryType.objects.all(), source='delivery_type', write_only=True, required=False, allow_null=True )
    document_type_id = serializers.PrimaryKeyRelatedField( queryset=DocumentType.objects.all(), source='document_type', write_only=True, required=False, allow_null=True )
    journal_id = serializers.PrimaryKeyRelatedField( queryset=Journal.objects.all(), source='journal', write_only=True, required=False, allow_null=True )
    signer_type_id = serializers.PrimaryKeyRelatedField( queryset=Signer.objects.all(), source='signer_type', write_only=True, required=False, allow_null=True )
    sender_id = serializers.PrimaryKeyRelatedField( queryset=Sender.objects.all(), source='sender', write_only=True, required=False, allow_null=True )
    class Meta:
        model = IncomingDocument
        fields = [ 'id', 'user', 'in_number', 'reg_number', 'reg_data', 'in_date', 'out_number', 'delivery_type', 'delivery_type_id', 'document_type', 'document_type_id', 'journal', 'journal_id', 'sender', 
                  'sender_id', 'signer_type', 'signer_type_id', 'title', 'summary', 'status', 'attachments', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at', 'status', 'user']

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        fields_to_fix = ['delivery_type', 'document_type', 'journal', 'sender']
        for field in fields_to_fix:
            if ret.get(field) is None:
                ret[field] = {'id': None, 'name': ""}
        return ret