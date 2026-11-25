"""Testlar uchun umumiy yordamchilar."""
import shutil
import tempfile

from django.contrib.auth.models import Group
from django.test import override_settings
from rest_framework.test import APITestCase

from flow_user.models import CustomUser, Department


class BaseAPITestCase(APITestCase):
    """Rollar bo'yicha tayyor foydalanuvchilar va vaqtinchalik MEDIA_ROOT."""

    @classmethod
    def setUpClass(cls):
        cls._media_dir = tempfile.mkdtemp(prefix="dms_test_media_")
        cls._media_override = override_settings(MEDIA_ROOT=cls._media_dir)
        cls._media_override.enable()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls._media_override.disable()
        shutil.rmtree(cls._media_dir, ignore_errors=True)

    @classmethod
    def setUpTestData(cls):
        cls.department = Department.objects.create(name="Bo'lim")
        cls.admin = cls.make_user("admin_user", "admin")
        cls.devonxona = cls.make_user("devonxona_user", "devonxona")
        cls.user = cls.make_user("oddiy_user", "user")
        cls.other_user = cls.make_user("boshqa_user", "user")
        cls.rector = cls.make_user("rektor_user", "user", is_rector=True)

    @classmethod
    def make_user(cls, username, group=None, **extra):
        user = CustomUser.objects.create_user(
            username=username,
            password="Parol12345!",
            first_name=username.title(),
            last_name="Familiya",
            department=extra.pop("department", None) or Department.objects.first(),
            **extra,
        )
        if group:
            user.groups.add(Group.objects.get_or_create(name=group)[0])
        return user

    def login(self, user):
        self.client.force_authenticate(user=user)
