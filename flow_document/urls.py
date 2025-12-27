from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    DeliveryTypeViewSet, 
    DocumentTypeViewSet,
    JournalViewSet,
    SenderViewSet,
    IncomingDocumentViewSet,
    AttachmentViewSet
)

router = DefaultRouter()
# Vue'dagi manzillar o'zgarmasligi uchun r'...' qismidagi nomlarni asl holida qoldiramiz
router.register(r'delivery-types', DeliveryTypeViewSet, basename='delivery-type')
router.register(r'document-types', DocumentTypeViewSet, basename='document-type')
router.register(r'journals', JournalViewSet, basename='journal')
router.register(r'senders', SenderViewSet, basename='sender')

# SIZNING ASL NOMINGIZ: incomingdocuments
router.register(r'incomingdocuments', IncomingDocumentViewSet, basename='incomingdocument')

router.register(r'attachments', AttachmentViewSet, basename='attachment')

urlpatterns = [
    path('', include(router.urls)),
]