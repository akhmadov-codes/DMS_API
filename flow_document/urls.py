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
router.register(r'delivery-types', DeliveryTypeViewSet)
router.register(r'document-types', DocumentTypeViewSet)
router.register(r'journals', JournalViewSet)
router.register(r'senders', SenderViewSet)
router.register(r'incomingdocuments', IncomingDocumentViewSet)
router.register(r'attachments', AttachmentViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
