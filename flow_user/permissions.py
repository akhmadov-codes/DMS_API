"""
Rollar bo'yicha ruxsatlar. Frontenddagi rollar bilan bir xil:

* admin      - tizim administratori
* devonxona  - hujjatlar bilan ishlovchi (manager)
* user       - oddiy xodim / ijrochi
* is_rector  - rahbar (CustomUser.is_rector), topshiriqlarni tahrirlay oladi
"""
from rest_framework.permissions import SAFE_METHODS, BasePermission

MANAGER_GROUPS = ("admin", "devonxona")


def _group_names(user):
    """Foydalanuvchi guruhlarini bitta so'rov bilan olib, request davomida keshlaydi."""
    if not user or not user.is_authenticated:
        return set()
    cached = getattr(user, "_group_names_cache", None)
    if cached is None:
        cached = set(user.groups.values_list("name", flat=True))
        user._group_names_cache = cached
    return cached


def is_admin(user):
    return "admin" in _group_names(user)


def is_manager(user):
    return bool(_group_names(user) & set(MANAGER_GROUPS))


def is_rector(user):
    return bool(user and user.is_authenticated and getattr(user, "is_rector", False))


class IsAdminOrReadOnly(BasePermission):
    """O'qish - barcha kirganlar, yozish - faqat admin."""

    message = "Bu amal faqat administrator uchun."

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        return request.method in SAFE_METHODS or is_admin(request.user)


class IsManagerOrReadOnly(BasePermission):
    """O'qish - barcha kirganlar, yozish - admin yoki devonxona."""

    message = "Bu amal faqat admin yoki devonxona uchun."

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        return request.method in SAFE_METHODS or is_manager(request.user)


class IsManagerRectorOrReadOnly(BasePermission):
    """O'qish - barcha kirganlar, yozish - admin, devonxona yoki rektor."""

    message = "Bu amal faqat admin, devonxona yoki rahbar uchun."

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return True
        return is_manager(request.user) or is_rector(request.user)
