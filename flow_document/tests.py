from django.core.files.uploadedfile import SimpleUploadedFile

from flow_document.models import Attachment, IncomingDocument, Journal, Signer
from flow_user.testing import BaseAPITestCase


class SignerApiTests(BaseAPITestCase):
    def setUp(self):
        self.signer = Signer.objects.create(last_name="Karimov", first_name="Anvar")

    def test_put_updates_signer(self):
        """Frontend imzolovchini PUT bilan yangilaydi."""
        self.login(self.devonxona)
        resp = self.client.put(f"/api/signer/{self.signer.id}/", {"last_name": "Aliyev", "first_name": "Vali"}, format="json")
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(resp.data["result"]["full_name"], "A.Vali")
        self.signer.refresh_from_db()
        self.assertEqual(self.signer.last_name, "Aliyev")

    def test_patch_updates_signer(self):
        self.login(self.devonxona)
        resp = self.client.patch(f"/api/signer/{self.signer.id}/", {"first_name": "Bobur"}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.signer.refresh_from_db()
        self.assertEqual(self.signer.first_name, "Bobur")

    def test_signer_without_last_name(self):
        Signer.objects.create(first_name="Faqat ism")
        self.login(self.user)
        resp = self.client.get("/api/signer/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(".Faqat ism", [s["full_name"] for s in resp.data["result"]])

    def test_user_cannot_modify_signer(self):
        self.login(self.user)
        self.assertEqual(self.client.put(f"/api/signer/{self.signer.id}/", {"last_name": "X", "first_name": "Y"}, format="json").status_code, 403)
        self.assertEqual(self.client.delete(f"/api/signer/{self.signer.id}/").status_code, 403)


class IncomingDocumentApiTests(BaseAPITestCase):
    def test_manager_creates_document_as_draft(self):
        journal = Journal.objects.create(name="Jurnal")
        self.login(self.devonxona)
        resp = self.client.post("/api/incomingdocuments/", {"title": "Xat", "journal_id": journal.id}, format="json")
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data["status"], "draft")
        self.assertEqual(resp.data["user"], self.devonxona.id)
        self.assertEqual(resp.data["journal"]["name"], "Jurnal")
        # Bo'sh bog'lanishlar frontend kutgan ko'rinishda
        self.assertEqual(resp.data["sender"], {"id": None, "name": ""})

    def test_user_can_read_but_not_write_documents(self):
        doc = IncomingDocument.objects.create(user=self.devonxona, title="Xat")
        self.login(self.user)
        self.assertEqual(self.client.get("/api/incomingdocuments/").status_code, 200)
        self.assertEqual(self.client.post("/api/incomingdocuments/", {"title": "X"}, format="json").status_code, 403)
        self.assertEqual(self.client.delete(f"/api/incomingdocuments/{doc.id}/").status_code, 403)

    def test_search_by_signer(self):
        signer = Signer.objects.create(last_name="Toshmatov", first_name="Ali")
        IncomingDocument.objects.create(user=self.devonxona, title="Birinchi", signer_type=signer)
        IncomingDocument.objects.create(user=self.devonxona, title="Ikkinchi")
        self.login(self.devonxona)
        resp = self.client.get("/api/incomingdocuments/?search=Toshmatov")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual([d["title"] for d in resp.data["results"]], ["Birinchi"])

    def test_filters_used_by_frontend(self):
        IncomingDocument.objects.create(user=self.devonxona, title="A", in_number="12/5", status="attached")
        IncomingDocument.objects.create(user=self.devonxona, title="B", in_number="99")
        self.login(self.devonxona)
        resp = self.client.get("/api/incomingdocuments/?page=1&status=attached&in_number=12/5")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["count"], 1)


class AttachmentApiTests(BaseAPITestCase):
    def test_upload_sets_status_and_extension(self):
        doc = IncomingDocument.objects.create(user=self.devonxona, title="Xat")
        self.login(self.devonxona)
        resp = self.client.post("/api/attachments/", {
            "document_id": doc.id,
            "files": [
                SimpleUploadedFile("hujjat.PDF", b"%PDF-1.4", content_type="application/pdf"),
                SimpleUploadedFile("ilova.docx", b"docx"),
            ],
        }, format="multipart")
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(sorted(a["extension"] for a in resp.data), ["docx", "pdf"])
        self.assertEqual(sorted(Attachment.objects.values_list("extension", flat=True)), ["docx", "pdf"])
        doc.refresh_from_db()
        self.assertEqual(doc.status, "attached")

        # Oxirgi fayl o'chirilsa - qoralamaga qaytadi
        for attachment in Attachment.objects.all():
            self.assertEqual(self.client.delete(f"/api/attachments/{attachment.id}/").status_code, 204)
        doc.refresh_from_db()
        self.assertEqual(doc.status, "draft")

    def test_user_cannot_upload(self):
        doc = IncomingDocument.objects.create(user=self.devonxona, title="Xat")
        self.login(self.user)
        resp = self.client.post("/api/attachments/", {
            "document_id": doc.id, "files": [SimpleUploadedFile("a.pdf", b"x")],
        }, format="multipart")
        self.assertEqual(resp.status_code, 403)
