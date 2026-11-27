from django.core.files.uploadedfile import SimpleUploadedFile

from flow_document.models import IncomingDocument
from flow_task.models import Task, TaskAssignee
from flow_taskres.models import TaskResponse, TaskResponseFile
from flow_user.testing import BaseAPITestCase


class TaskResponseTests(BaseAPITestCase):
    def setUp(self):
        document = IncomingDocument.objects.create(user=self.devonxona, title="Xat")
        self.task = Task.objects.create(document=document)
        TaskAssignee.objects.create(task=self.task, user=self.user, order=1)

    def create_response(self, user=None, files=()):
        self.login(user or self.user)
        data = {"task": self.task.id, "description": "Bajarildi"}
        if files:
            data["uploaded_files"] = list(files)
        return self.client.post("/api/task-responses/", data, format="multipart")

    def test_assignee_response_moves_task_to_confirmation(self):
        resp = self.create_response(files=[SimpleUploadedFile("hisobot.XLSX", b"x")])
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data["files"][0]["extension"], "xlsx")
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, "in_confirmation")

    def test_not_assigned_user_cannot_respond(self):
        resp = self.create_response(user=self.other_user)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(TaskResponse.objects.count(), 0)

    def test_patch_without_task_field(self):
        resp = self.create_response()
        response_id = resp.data["id"]
        Task.objects.filter(id=self.task.id).update(status="in_progress")
        resp = self.client.patch(f"/api/task-responses/{response_id}/", {"description": "Yangilandi"}, format="multipart")
        self.assertEqual(resp.status_code, 200, resp.data)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, "in_confirmation")

    def test_frontend_style_patch_with_task_and_files(self):
        resp = self.create_response()
        resp = self.client.patch(f"/api/task-responses/{resp.data['id']}/", {
            "task": self.task.id, "description": "Yangi", "uploaded_files": [SimpleUploadedFile("b.pdf", b"x")],
        }, format="multipart")
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(len(resp.data["files"]), 1)

    def test_other_user_cannot_edit_response(self):
        resp = self.create_response()
        self.login(self.other_user)
        resp = self.client.patch(f"/api/task-responses/{resp.data['id']}/", {"description": "X"}, format="multipart")
        self.assertEqual(resp.status_code, 403)

    def test_file_delete_only_by_owner_or_manager(self):
        self.create_response(files=[SimpleUploadedFile("a.pdf", b"x"), SimpleUploadedFile("b.pdf", b"y")])
        first, second = TaskResponseFile.objects.order_by("id")

        self.login(self.other_user)
        self.assertEqual(self.client.delete(f"/api/task-response-files/{first.id}/").status_code, 403)

        self.login(self.user)
        self.assertEqual(self.client.delete(f"/api/task-response-files/{first.id}/").status_code, 204)

        self.login(self.devonxona)
        self.assertEqual(self.client.delete(f"/api/task-response-files/{second.id}/").status_code, 204)
        self.assertEqual(TaskResponseFile.objects.count(), 0)
