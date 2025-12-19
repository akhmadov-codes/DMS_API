from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    DeliveryTypeViewSet,
    JournalViewSet,
    SenderViewSet,
    IncomingDocumentViewSet,
    AttachmentViewSet
)

router = DefaultRouter()
router.register(r'delivery-types', DeliveryTypeViewSet)
router.register(r'journals', JournalViewSet)
router.register(r'senders', SenderViewSet)
router.register(r'documents', IncomingDocumentViewSet)
router.register(r'attachments', AttachmentViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
