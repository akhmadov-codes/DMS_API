from flow_user.models import CustomUser
from flow_user.testing import BaseAPITestCase


class UserApiTests(BaseAPITestCase):
    def test_admin_creates_user_with_default_group(self):
        self.login(self.admin)
        resp = self.client.post("/api/users/", {
            "username": "yangi", "password": "YangiParol123", "first_name": "A",
            "last_name": "B", "department_id": self.department.id,
        }, format="json")
        self.assertEqual(resp.status_code, 201, resp.data)
        user = CustomUser.objects.get(username="yangi")
        self.assertTrue(user.check_password("YangiParol123"))
        self.assertEqual(list(user.groups.values_list("name", flat=True)), ["user"])

    def test_create_requires_password(self):
        self.login(self.admin)
        resp = self.client.post("/api/users/", {
            "username": "parolsiz", "department_id": self.department.id,
        }, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("password", resp.data)

    def test_admin_updates_user_without_password(self):
        """Frontend tahrirlashda parol bo'sh bo'lsa uni yubormaydi (PUT)."""
        self.login(self.admin)
        resp = self.client.put(f"/api/users/{self.user.id}/", {
            "username": self.user.username, "first_name": "Yangi ism",
            "last_name": "F", "department_id": self.department.id,
        }, format="json")
        self.assertEqual(resp.status_code, 200, resp.data)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Yangi ism")
        self.assertTrue(self.user.check_password("Parol12345!"))

    def test_admin_changes_password(self):
        self.login(self.admin)
        resp = self.client.patch(f"/api/users/{self.user.id}/", {"password": "BoshqaParol99"}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("BoshqaParol99"))

    def test_non_admin_can_read_but_not_write_users(self):
        for actor in (self.user, self.devonxona, self.rector):
            self.login(actor)
            self.assertEqual(self.client.get("/api/users/?search=Admin").status_code, 200)
            resp = self.client.patch(f"/api/users/{self.admin.id}/", {"password": "Buzgunchi123"}, format="json")
            self.assertEqual(resp.status_code, 403)
            self.assertEqual(self.client.delete(f"/api/users/{self.other_user.id}/").status_code, 403)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.check_password("Parol12345!"))

    def test_anonymous_is_rejected(self):
        self.assertEqual(self.client.get("/api/users/").status_code, 401)

    def test_profile(self):
        self.login(self.user)
        resp = self.client.get("/api/profile/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["groups"], ["user"])

    def test_departments_permissions(self):
        self.login(self.user)
        self.assertEqual(self.client.get("/api/departments/").status_code, 200)
        self.assertEqual(self.client.post("/api/departments/", {"name": "X"}, format="json").status_code, 403)
        self.login(self.devonxona)
        self.assertEqual(self.client.post("/api/departments/", {"name": "X"}, format="json").status_code, 201)


class AuthApiTests(BaseAPITestCase):
    def test_token_returns_access_and_user_id(self):
        resp = self.client.post("/api/token/auth/", {"username": "oddiy_user", "password": "Parol12345!"}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("access", resp.data)
        self.assertEqual(resp.data["user_id"], self.user.id)

    def test_logout_endpoint_exists(self):
        self.assertEqual(self.client.post("/api/logout/").status_code, 204)
