# config/settings_prod.py
# Import
import logging
import os
from datetime import timedelta

from django.conf import settings

# Rest framework conf
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    )
}
# Cors conf
CORS_ALLOW_ALL_ORIGINS = False
# CORS uchun ruxsat:
CORS_ALLOWED_ORIGINS = [
    "https://exa.tipme.uz",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
]
# CSRF uchun ruxsat:
CSRF_TRUSTED_ORIGINS = [
    "https://api-edo.tipme.uz",
    "https://exa.tipme.uz",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
]
# Simpl JWT conf
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=1),  # Access token 1 kun amal qiladi
    "REFRESH_TOKEN_LIFETIME": timedelta(
        days=7
    ),  # Refresh token muddati, istalgancha sozlash mumkin
    "ROTATE_REFRESH_TOKENS": False,
    "BLACKLIST_AFTER_ROTATION": True,
}

# Swagger conf
SWAGGER_SETTINGS = {
    "SECURITY_DEFINITIONS": {
        "Bearer": {"type": "apiKey", "name": "Authorization", "in": "header"}
    },
    "USE_SESSION_AUTH": False,  # Session authni o'chirish JWT bilan ishlashda xatolarni kamaytiradi
    "JSON_EDITOR": True,
    "PERSIST_AUTH": True,
    "DEFAULT_SCHEMES": [
        "https",
    ],
    "DEFAULT_API_URL": "https://api-edo.tipme.uz/" if not settings.DEBUG else None,
}

# Mixed Content va HTTPS
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True

# Cookie xavfsizligi
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# 3. Brauzer xavfsizlik (HSTS)
SECURE_HSTS_SECONDS = 31536000  # 1 yil
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Redirect sozlamasi
# Eslatma: Nginx o'zi redirect qilayotgan bo'lsa, buni False qoldiring
SECURE_SSL_REDIRECT = False

#  Admin panel miltillashiga qarshi
SECURE_REFERRER_POLICY = "same-origin"

# Brauzer keshini boshqarish uchun (statik fayllar yangilanganda muammo bo'lmasligi uchun)
if not getattr(settings, "DEBUG", True):
    STATICFILES_STORAGE = (
        "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"
    )

# Statik fayllar brauzer keshida uzoqroq qolishi uchun (miltillashni kamaytiradi)
AWS_S3_OBJECT_PARAMETERS = {
    "CacheControl": "max-age=2592000",
}

# Faqat ERROR va yuqori loglar
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_FILE = os.path.join(BASE_DIR, "logs/server_errors.log")
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.ERROR,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
