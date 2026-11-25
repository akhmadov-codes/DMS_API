from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions
from rest_framework_simplejwt.views import TokenRefreshView

from flow_user.views import LogoutView, MyTokenObtainPairView

schema_view = get_schema_view(
    openapi.Info(
        title="Document Flow API",
        default_version="v1",
        description="Document Flow Project API documentation",
    ),
    url=settings.API_PUBLIC_URL if not settings.DEBUG else None,
    public=True,
    permission_classes=[permissions.AllowAny],
    authentication_classes=[],
)

urlpatterns = [
    path("secret-office/", admin.site.urls),
    # JWT
    path("api/token/auth/", MyTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/auth/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/logout/", LogoutView.as_view(), name="logout"),
    # Ilovalar
    path("api/", include("flow_user.urls")),
    path("api/", include("flow_document.urls")),
    path("api/", include("flow_task.urls")),
    path("api/", include("flow_taskres.urls")),
    # Swagger va Redoc
    path("swagger/", schema_view.with_ui("swagger", cache_timeout=0), name="schema-swagger-ui"),
    path("redoc/", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
