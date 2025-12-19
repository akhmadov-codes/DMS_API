from rest_framework import serializers
from .models import DeliveryType, Journal, Sender, IncomingDocument, Attachment

# ==== Lookup / Directory Models ====
class DeliveryTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryType
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
    class Meta:
        model = Attachment
        fields = ['id', 'file', 'extension', 'created_at']
        read_only_fields = ['created_at', 'extension']


# ==== IncomingDocument Serializer ====
class IncomingDocumentSerializer(serializers.ModelSerializer):
    # Nested read-only fields
    delivery_type = DeliveryTypeSerializer(read_only=True)
    journal = JournalSerializer(read_only=True)
    sender = SenderSerializer(read_only=True)
    
    # Write-only ForeignKey fields
    delivery_type_id = serializers.PrimaryKeyRelatedField(
        queryset=DeliveryType.objects.all(), write_only=True, source='delivery_type', required=False
    )
    journal_id = serializers.PrimaryKeyRelatedField(
        queryset=Journal.objects.all(), write_only=True, source='journal', required=False
    )
    sender_id = serializers.PrimaryKeyRelatedField(
        queryset=Sender.objects.all(), write_only=True, source='sender', required=False
    )

    # Nested attachments read-only
    attachments = AttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = IncomingDocument
        fields = [
            'id', 'user', 'in_number', 'out_number',
            'delivery_type', 'delivery_type_id',
            'signer', 'journal', 'journal_id',
            'title', 'sender', 'sender_id',
            'summary', 'status', 'attachments',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
