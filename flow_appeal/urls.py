from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AppealFormViewSet,
    AppealForwardingViewSet,
    AppealKindViewSet,
    AppealQuestionViewSet,
    OralAppealViewSet,
    ReceptionTypeViewSet,
)

router = DefaultRouter()
router.register(r"appeals", OralAppealViewSet, basename="appeals")
router.register(r"appeal-forwardings", AppealForwardingViewSet, basename="appeal-forwardings")
router.register(r"appeal-questions", AppealQuestionViewSet, basename="appeal-questions")
router.register(r"appeal-forms", AppealFormViewSet, basename="appeal-forms")
router.register(r"appeal-kinds", AppealKindViewSet, basename="appeal-kinds")
router.register(r"reception-types", ReceptionTypeViewSet, basename="reception-types")

urlpatterns = [
    path("", include(router.urls)),
]
