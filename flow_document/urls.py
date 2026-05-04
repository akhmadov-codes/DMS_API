from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    DeliveryTypeViewSet, 
    DocumentTypeViewSet,
    JournalViewSet,
    SenderViewSet,
    IncomingDocumentViewSet,
    AttachmentViewSet, 
    SignercollectionViews, SignerinstanceViews
)

router = DefaultRouter()

router.register(r'delivery-types', DeliveryTypeViewSet, basename='delivery-type')
router.register(r'document-types', DocumentTypeViewSet, basename='document-type')
router.register(r'journals', JournalViewSet, basename='journal')
router.register(r'senders', SenderViewSet, basename='sender')

router.register(r'incomingdocuments', IncomingDocumentViewSet, basename='incomingdocument')
router.register(r'attachments', AttachmentViewSet, basename='attachment')

urlpatterns = [
    path('', include(router.urls)),
    path('signer/', SignercollectionViews.as_view(), name='signer'),
    path('signer/<int:id>/', SignerinstanceViews.as_view(), name='signer')
]