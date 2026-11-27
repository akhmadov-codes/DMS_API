from datetime import timedelta
from io import StringIO

from django.core.management import call_command
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from flow_document.models import IncomingDocument
from flow_task.models import Subject, Task, TaskAssignee, TaskDescription
from flow_taskres.models import TaskResponse
from flow_user.testing import BaseAPITestCase


class TaskTestMixin:
    def setUp(self):
        self.document = IncomingDocument.objects.create(user=self.devonxona, title="Kiruvchi xat")
        self.subject = Subject.objects.create(title="Mavzu")
        self.description = TaskDescription.objects.create(title="Ijro uchun")

    def payload(self, assignees, **extra):
        data = {
            "document_id": self.document.id,
            "subject_id": self.subject.id,
            "task_description_id": self.description.id,
            "due_date": str(timezone.localdate() + timedelta(days=3)),
            "description": "Izoh",
            "assignees_ids": assignees,
        }
        data.update(extra)
        return data

    def make_task(self, assignees=(), **extra):
        task = Task.objects.create(
            document=self.document, subject=self.subject, task_description=self.description, **extra
        )
        for index, user in enumerate(assignees, start=1):
            TaskAssignee.objects.create(task=task, user=user, order=index)
        return task


class TaskCreateUpdateTests(TaskTestMixin, BaseAPITestCase):
    def test_create_keeps_assignee_order_and_sets_creator(self):
        self.login(self.devonxona)
        ids = [self.other_user.id, self.user.id]
        resp = self.client.post("/api/tasks/", self.payload([str(i) for i in ids]), format="json")
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual([a["id"] for a in resp.data["assignees"]], ids)
        self.assertEqual([a["order"] for a in resp.data["assignees"]], [1, 2])
        self.assertEqual(resp.data["status"], "in_progress")
        self.assertEqual(Task.objects.get(id=resp.data["id"]).creator, self.devonxona)

    def test_create_for_all_users(self):
        self.login(self.devonxona)
        resp = self.client.post("/api/tasks/", self.payload(["all-users"]), format="json")
        self.assertEqual(resp.status_code, 201, resp.data)
        task = Task.objects.get(id=resp.data["id"])
        self.assertEqual(task.assignees.count(), 5)

    def test_invalid_assignee_returns_400_and_creates_nothing(self):
        self.login(self.devonxona)
        for bad in (["abc"], [str(self.user.id), "999999"]):
            resp = self.client.post("/api/tasks/", self.payload(bad), format="json")
            self.assertEqual(resp.status_code, 400)
            self.assertIn("assignees_ids", resp.data)
        self.assertEqual(Task.objects.count(), 0)

    def test_duplicate_assignee_ids_are_ignored(self):
        self.login(self.devonxona)
        resp = self.client.post("/api/tasks/", self.payload([str(self.user.id), str(self.user.id)]), format="json")
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(len(resp.data["assignees"]), 1)

    def test_update_replaces_assignees(self):
        task = self.make_task([self.user])
        self.login(self.devonxona)
        resp = self.client.patch(f"/api/tasks/{task.id}/", {"assignees_ids": [str(self.other_user.id)]}, format="json")
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual([a["id"] for a in resp.data["assignees"]], [self.other_user.id])

    def test_rector_can_edit_assigned_task(self):
        task = self.make_task([self.rector])
        self.login(self.rector)
        resp = self.client.patch(f"/api/tasks/{task.id}/", self.payload([str(self.rector.id), str(self.user.id)]), format="json")
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(len(resp.data["assignees"]), 2)

    def test_regular_user_cannot_create_edit_or_delete(self):
        task = self.make_task([self.user])
        self.login(self.user)
        self.assertEqual(self.client.post("/api/tasks/", self.payload([str(self.user.id)]), format="json").status_code, 403)
        self.assertEqual(self.client.patch(f"/api/tasks/{task.id}/", {"status": "done"}, format="json").status_code, 403)
        self.assertEqual(self.client.delete(f"/api/tasks/{task.id}/").status_code, 403)
        task.refresh_from_db()
        self.assertEqual(task.status, "in_progress")

    def test_rector_cannot_delete(self):
        task = self.make_task([self.rector])
        self.login(self.rector)
        self.assertEqual(self.client.delete(f"/api/tasks/{task.id}/").status_code, 403)

    def test_deleting_task_description_keeps_tasks(self):
        task = self.make_task([self.user])
        self.login(self.devonxona)
        self.assertEqual(self.client.delete(f"/api/taskdiscriptions/{self.description.id}/").status_code, 204)
        task.refresh_from_db()
        self.assertIsNone(task.task_description)

    def test_rector_can_add_task_description_user_cannot(self):
        self.login(self.user)
        self.assertEqual(self.client.post("/api/taskdiscriptions/", {"title": "X"}, format="json").status_code, 403)
        self.login(self.rector)
        self.assertEqual(self.client.post("/api/taskdiscriptions/", {"title": "X"}, format="json").status_code, 201)


class TaskListTests(TaskTestMixin, BaseAPITestCase):
    def test_user_sees_only_assigned_tasks_with_stats(self):
        mine = self.make_task([self.user])
        self.make_task([self.other_user], status="done")
        self.login(self.user)
        resp = self.client.get("/api/tasks/?page=1")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual([t["id"] for t in resp.data["results"]], [mine.id])
        self.assertEqual(resp.data["all_tasks"], 1)
        self.assertEqual(resp.data["in_progress"], 1)
        self.assertEqual(resp.data["done"], 0)

    def test_manager_sees_all_tasks_and_filters(self):
        self.make_task([self.user])
        self.make_task([self.other_user], status="done")
        self.login(self.devonxona)
        resp = self.client.get("/api/tasks/?page=1&status=done")
        self.assertEqual(resp.data["count"], 1)
        self.assertEqual(resp.data["all_tasks"], 2)
        self.assertEqual(resp.data["done"], 1)
        resp = self.client.get(f"/api/tasks/?assignee={self.user.id}")
        self.assertEqual(resp.data["count"], 1)

    def test_query_count_does_not_grow_with_tasks(self):
        """Ijrochilar soni va topshiriqlar soni oshganda so'rovlar soni o'zgarmasligi kerak (N+1 yo'q)."""
        self.login(self.devonxona)
        everyone = [self.admin, self.devonxona, self.user, self.other_user, self.rector]

        def count_queries():
            # Har bir haqiqiy so'rovda foydalanuvchi bazadan yangidan yuklanadi
            self.login(type(self.devonxona).objects.get(pk=self.devonxona.pk))
            with CaptureQueriesContext(connection) as ctx:
                resp = self.client.get("/api/tasks/?page=1")
            self.assertEqual(resp.status_code, 200)
            return len(ctx.captured_queries)

        for _ in range(2):
            task = self.make_task(everyone)
            TaskResponse.objects.create(task=task, user=self.user, description="javob")
        small = count_queries()
        for _ in range(6):
            task = self.make_task(everyone)
            TaskResponse.objects.create(task=task, user=self.user, description="javob")
        big = count_queries()
        self.assertEqual(small, big)

    def test_assignees_are_returned_in_order(self):
        task = self.make_task([self.rector, self.user, self.other_user])
        self.login(self.devonxona)
        resp = self.client.get("/api/tasks/")
        data = next(t for t in resp.data["results"] if t["id"] == task.id)
        self.assertEqual([a["id"] for a in data["assignees"]], [self.rector.id, self.user.id, self.other_user.id])
        self.assertEqual(set(data["assignees"][0]), {"task_assignee_id", "order", "id", "last_name", "first_name", "father_name", "department_name"})


    def test_filter_by_document_and_due_range(self):
        today = timezone.localdate()
        other_doc = IncomingDocument.objects.create(user=self.devonxona, title="Boshqa xat")
        a = self.make_task([self.user], due_date=today)
        b = self.make_task([self.user], due_date=today + timedelta(days=10))
        c = Task.objects.create(document=other_doc, subject=self.subject, due_date=today)
        self.login(self.devonxona)
        ids = lambda q: sorted(t["id"] for t in self.client.get(f"/api/tasks/?{q}").data["results"])
        self.assertEqual(ids(f"document={self.document.id}"), sorted([a.id, b.id]))
        self.assertEqual(ids(f"due_from={today}&due_to={today + timedelta(days=5)}"), sorted([a.id, c.id]))
        self.assertEqual(ids(f"due_from={today + timedelta(days=10)}&due_to={today + timedelta(days=10)}"), [b.id])


class TaskStatusTests(TaskTestMixin, BaseAPITestCase):
    def test_only_manager_changes_status_rector_can_edit(self):
        task = self.make_task([self.rector], status="in_confirmation")
        self.login(self.rector)
        resp = self.client.patch(f"/api/tasks/{task.id}/", {"status": "done"}, format="json")
        self.assertEqual(resp.status_code, 403)
        task.refresh_from_db()
        self.assertEqual(task.status, "in_confirmation")
        resp = self.client.patch(f"/api/tasks/{task.id}/", {"description": "Yangi izoh"}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.login(self.user)
        self.assertEqual(self.client.patch(f"/api/tasks/{task.id}/", {"status": "done"}, format="json").status_code, 403)
        self.login(self.devonxona)
        self.assertEqual(self.client.patch(f"/api/tasks/{task.id}/", {"status": "done"}, format="json").status_code, 200)

    """Mavjud status mantig'ini qayd etuvchi testlar (o'zgarmasligi kerak)."""

    def test_done_stays_done_when_answered_in_time(self):
        task = self.make_task([self.user], due_date=timezone.localdate() + timedelta(days=1), status="in_confirmation")
        TaskResponse.objects.create(task=task, user=self.user, description="javob")
        self.login(self.devonxona)
        resp = self.client.patch(f"/api/tasks/{task.id}/", {"status": "done"}, format="json")
        self.assertEqual(resp.status_code, 200)
        task.refresh_from_db()
        self.assertEqual(task.status, "done")

    def test_done_becomes_done_overdue_when_answered_late(self):
        task = self.make_task([self.user], due_date=timezone.localdate() - timedelta(days=2), status="in_confirmation")
        TaskResponse.objects.create(task=task, user=self.user, description="kech javob")
        self.login(self.devonxona)
        resp = self.client.patch(f"/api/tasks/{task.id}/", {"status": "done"}, format="json")
        self.assertEqual(resp.status_code, 200)
        task.refresh_from_db()
        self.assertEqual(task.status, "done_overdue")

    def test_manager_returns_task_to_progress(self):
        task = self.make_task([self.user], status="in_confirmation")
        self.login(self.devonxona)
        resp = self.client.patch(f"/api/tasks/{task.id}/", {"status": "in_progress"}, format="json")
        self.assertEqual(resp.status_code, 200)
        task.refresh_from_db()
        self.assertEqual(task.status, "in_progress")

    def test_check_tasks_command(self):
        yesterday = timezone.localdate() - timedelta(days=1)
        overdue_progress = self.make_task([self.user], due_date=yesterday)
        overdue_confirm = self.make_task([self.user], due_date=yesterday, status="in_confirmation")
        overdue_done = self.make_task([self.user], due_date=yesterday, status="done")
        due_today = self.make_task([self.user], due_date=timezone.localdate())
        out = StringIO()
        call_command("check_tasks", stdout=out)
        self.assertIn("2 ta vazifa yangilandi", out.getvalue())
        statuses = {t.id: t.status for t in Task.objects.all()}
        self.assertEqual(statuses[overdue_progress.id], "be_rejected")
        self.assertEqual(statuses[overdue_confirm.id], "be_rejected")
        self.assertEqual(statuses[overdue_done.id], "done")
        self.assertEqual(statuses[due_today.id], "in_progress")
