import os
import tempfile
from datetime import timedelta
from io import StringIO

from django.core.management import call_command
from django.utils import timezone

from flow_document.models import IncomingDocument, Sender, Signer
from flow_task.models import Subject, Task, TaskAssignee, TaskDescription
from flow_taskres.models import TaskResponse
from flow_user.testing import BaseAPITestCase

from .models import AppealForm, AppealKind, AppealQuestion, OralAppeal, ReceptionType

TODAY = timezone.localdate


class AppealTestMixin:
    def setUp(self):
        self.signer = Signer.objects.create(last_name="Rahbarov", first_name="Rahbar")
        self.subject = Subject.objects.create(title="Mavzu")
        self.description = TaskDescription.objects.create(title="Ko'rib chiqish uchun")

    def payload(self, **extra):
        data = {
            "applicant_name": "Aliyev Vali",
            "applicant_type": "individual",
            "address": "Toshkent sh.",
            "received_date": str(TODAY()),
            "appeal_form_id": AppealForm.objects.get(name="Og'zaki").id,
            "appeal_kind_id": AppealKind.objects.get(name="Ariza").id,
            "reception_type_id": ReceptionType.objects.get(name="Shaxsiy qabul").id,
            "summary": "Mazmun",
            "signer_id": self.signer.id,
            "department_id": self.department.id,
        }
        data.update(extra)
        return data

    def make_appeal(self, **extra):
        extra.setdefault("applicant_name", "Murojaatchi")
        return OralAppeal.objects.create(received_date=TODAY(), **extra)

    def make_task(self, appeal, assignees=(), due_in=3, **extra):
        task = Task.objects.create(
            appeal=appeal, subject=self.subject, task_description=self.description,
            due_date=TODAY() + timedelta(days=due_in), **extra,
        )
        for index, user in enumerate(assignees, start=1):
            TaskAssignee.objects.create(task=task, user=user, order=index)
        return task


class AppealCreateTests(AppealTestMixin, BaseAPITestCase):
    def test_seed_references_exist(self):
        self.assertEqual(set(AppealKind.objects.values_list("name", flat=True)), {"Ariza", "Taklif", "Shikoyat"})
        self.assertEqual(AppealForm.objects.count(), 3)
        self.assertEqual(ReceptionType.objects.count(), 4)

    def test_create_assigns_sequential_number_and_creator(self):
        self.login(self.devonxona)
        first = self.client.post("/api/appeals/", self.payload(), format="json")
        second = self.client.post("/api/appeals/", self.payload(), format="json")
        self.assertEqual(first.status_code, 201, first.data)
        year = TODAY().year
        self.assertEqual(first.data["reg_number"], f"OM-{year}/0001")
        self.assertEqual(second.data["reg_number"], f"OM-{year}/0002")
        self.assertEqual(first.data["appeal_kind"]["name"], "Ariza")
        self.assertIsNone(first.data["task_status"])
        self.assertEqual(OralAppeal.objects.get(id=first.data["id"]).user, self.devonxona)

    def test_reg_number_cannot_be_changed(self):
        appeal = self.make_appeal()
        self.login(self.devonxona)
        resp = self.client.patch(f"/api/appeals/{appeal.id}/", {"reg_number": "X-1"}, format="json")
        self.assertEqual(resp.status_code, 200)
        appeal.refresh_from_db()
        self.assertTrue(appeal.reg_number.startswith("OM-"))

    def test_future_received_date_rejected(self):
        self.login(self.devonxona)
        resp = self.client.post("/api/appeals/", self.payload(received_date=str(TODAY() + timedelta(days=1))), format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("received_date", resp.data)

    def test_section_cannot_be_chosen_as_question(self):
        section = AppealQuestion.objects.create(code="01", name="Bo'lim")
        leaf = AppealQuestion.objects.create(code="01.01", name="Savol", parent=section)
        self.login(self.devonxona)
        resp = self.client.post("/api/appeals/", self.payload(question_id=section.id), format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("question_id", resp.json())
        resp = self.client.post("/api/appeals/", self.payload(question_id=leaf.id), format="json")
        self.assertEqual(resp.status_code, 201, resp.content)

    def test_user_cannot_create(self):
        self.login(self.user)
        resp = self.client.post("/api/appeals/", self.payload(), format="json")
        self.assertEqual(resp.status_code, 403)


class AppealVisibilityAndStatsTests(AppealTestMixin, BaseAPITestCase):
    def test_user_sees_only_assigned_appeals(self):
        mine = self.make_appeal()
        self.make_task(mine, [self.user, self.other_user])
        self.make_task(self.make_appeal(), [self.other_user])
        self.make_appeal()

        self.login(self.user)
        resp = self.client.get("/api/appeals/")
        self.assertEqual([a["id"] for a in resp.data["results"]], [mine.id])
        self.assertEqual(resp.data["all_appeals"], 1)

        self.login(self.devonxona)
        self.assertEqual(self.client.get("/api/appeals/").data["count"], 3)

    def test_status_filter_and_stats(self):
        no_task = self.make_appeal()
        in_progress = self.make_appeal()
        self.make_task(in_progress)
        overdue = self.make_appeal()
        self.make_task(overdue, due_in=-2)
        done = self.make_appeal()
        self.make_task(done, status="done")

        self.login(self.devonxona)
        data = self.client.get("/api/appeals/").data
        self.assertEqual(data["all_appeals"], 4)
        self.assertEqual(data["no_task"], 1)
        self.assertEqual(data["in_progress"], 2)
        self.assertEqual(data["done"], 1)
        self.assertEqual(data["overdue"], 1)
        by_id = {a["id"]: a for a in data["results"]}
        self.assertTrue(by_id[overdue.id]["is_overdue"])
        self.assertFalse(by_id[in_progress.id]["is_overdue"])

        ids = lambda q: {a["id"] for a in self.client.get(f"/api/appeals/?{q}").data["results"]}
        self.assertEqual(ids("status=no_task"), {no_task.id})
        self.assertEqual(ids("status=done"), {done.id})
        self.assertEqual(ids("overdue=true"), {overdue.id})

    def test_search_by_name_and_number(self):
        target = self.make_appeal(applicant_name="Karimova Dilnoza")
        self.make_appeal()
        self.login(self.devonxona)
        self.assertEqual([a["id"] for a in self.client.get("/api/appeals/?search=Dilnoza").data["results"]], [target.id])
        self.assertEqual([a["id"] for a in self.client.get(f"/api/appeals/?search={target.reg_number}").data["results"]], [target.id])


class AppealTaskIntegrationTests(AppealTestMixin, BaseAPITestCase):
    def task_payload(self, **extra):
        data = {
            "subject_id": self.subject.id,
            "task_description_id": self.description.id,
            "due_date": str(TODAY() + timedelta(days=5)),
            "assignees_ids": [str(self.user.id)],
        }
        data.update(extra)
        return data

    def test_create_task_for_appeal(self):
        appeal = self.make_appeal()
        self.login(self.devonxona)
        resp = self.client.post("/api/tasks/", self.task_payload(appeal_id=appeal.id), format="json")
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data["appeal"]["reg_number"], appeal.reg_number)
        self.assertIsNone(resp.data["document"])

        self.login(self.user)
        tasks = self.client.get("/api/tasks/?kind=appeal").data["results"]
        self.assertEqual([t["id"] for t in tasks], [resp.data["id"]])
        self.assertEqual(self.client.get("/api/tasks/?kind=document").data["count"], 0)

    def test_task_needs_exactly_one_of_document_or_appeal(self):
        appeal = self.make_appeal()
        document = IncomingDocument.objects.create(user=self.devonxona, title="Xat")
        self.login(self.devonxona)
        neither = self.client.post("/api/tasks/", self.task_payload(), format="json")
        self.assertEqual(neither.status_code, 400)
        both = self.client.post("/api/tasks/", self.task_payload(appeal_id=appeal.id, document_id=document.id), format="json")
        self.assertEqual(both.status_code, 400)
        self.assertEqual(Task.objects.count(), 0)

    def test_closing_task_records_who_and_when(self):
        appeal = self.make_appeal()
        task = self.make_task(appeal, [self.user])
        TaskResponse.objects.create(task=task, user=self.user, description="Bajarildi")
        self.login(self.devonxona)
        resp = self.client.patch(f"/api/tasks/{task.id}/", {"status": "done"}, format="json")
        self.assertEqual(resp.status_code, 200, resp.data)
        appeal.refresh_from_db()
        self.assertEqual(appeal.closed_by, self.devonxona)
        self.assertIsNotNone(appeal.closed_at)

    def test_extend_keeps_original_and_updates_open_tasks(self):
        appeal = self.make_appeal()
        task = self.make_task(appeal, [self.user], due_in=2)
        original = task.due_date
        new_due = TODAY() + timedelta(days=20)
        self.login(self.devonxona)
        resp = self.client.post(f"/api/appeals/{appeal.id}/extend/", {"new_due_date": str(new_due), "extended_by_id": self.signer.id}, format="json")
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(resp.data["original_due_date"], str(original))
        self.assertEqual(resp.data["extended_due_date"], str(new_due))
        self.assertEqual(resp.data["extended_by"]["id"], self.signer.id)
        task.refresh_from_db()
        self.assertEqual(task.due_date, new_due)

        # Ikkinchi uzaytirishda dastlabki muddat o'zgarmaydi
        later = new_due + timedelta(days=5)
        resp = self.client.post(f"/api/appeals/{appeal.id}/extend/", {"new_due_date": str(later), "extended_by_id": self.signer.id}, format="json")
        self.assertEqual(resp.data["original_due_date"], str(original))

    def test_extend_requires_open_task_and_manager(self):
        appeal = self.make_appeal()
        payload = {"new_due_date": str(TODAY() + timedelta(days=5)), "extended_by_id": self.signer.id}
        self.login(self.devonxona)
        self.assertEqual(self.client.post(f"/api/appeals/{appeal.id}/extend/", payload, format="json").status_code, 400)
        self.make_task(appeal, [self.user])
        self.login(self.user)
        self.assertEqual(self.client.post(f"/api/appeals/{appeal.id}/extend/", payload, format="json").status_code, 403)


class AppealForwardingTests(AppealTestMixin, BaseAPITestCase):
    def test_add_forwarding_and_see_it_in_appeal(self):
        appeal = self.make_appeal()
        org = Sender.objects.create(name="Tuman hokimligi")
        self.login(self.devonxona)
        resp = self.client.post("/api/appeal-forwardings/", {
            "appeal_id": appeal.id, "sent_date": str(TODAY()), "sent_to_id": org.id,
            "reply_number": "12/345", "reply_received_date": str(TODAY()),
        }, format="json")
        self.assertEqual(resp.status_code, 201, resp.data)
        detail = self.client.get(f"/api/appeals/{appeal.id}/").data
        self.assertEqual(detail["forwardings"][0]["sent_to"]["name"], "Tuman hokimligi")

    def test_reply_before_sent_rejected(self):
        appeal = self.make_appeal()
        self.login(self.devonxona)
        resp = self.client.post("/api/appeal-forwardings/", {
            "appeal_id": appeal.id, "sent_date": str(TODAY()),
            "reply_received_date": str(TODAY() - timedelta(days=1)),
        }, format="json")
        self.assertEqual(resp.status_code, 400)


class ImportQuestionsCommandTests(BaseAPITestCase):
    def test_import_builds_hierarchy_and_updates(self):
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8") as fh:
            fh.write("code;name;parent_code\n02.01;Pensiya;02\n02;Ijtimoiy ta'minot;\n")
            path = fh.name
        try:
            call_command("import_appeal_questions", path, stdout=StringIO())
            child = AppealQuestion.objects.get(code="02.01")
            self.assertEqual(child.parent.code, "02")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("code;name;parent_code\n02.01;Pensiya masalalari;02\n")
            call_command("import_appeal_questions", path, stdout=StringIO())
            self.assertEqual(AppealQuestion.objects.get(code="02.01").name, "Pensiya masalalari")
            self.assertEqual(AppealQuestion.objects.count(), 2)
        finally:
            os.remove(path)


class QuestionManagementApiTests(AppealTestMixin, BaseAPITestCase):
    URL = "/api/appeal-questions/"

    def test_list_has_usage_counts(self):
        section = AppealQuestion.objects.create(code="01", name="Bo'lim")
        child = AppealQuestion.objects.create(code="01.01", name="Savol", parent=section)
        self.make_appeal(question=child)
        self.login(self.user)
        rows = {r["code"]: r for r in self.client.get(self.URL).json()}
        self.assertEqual(rows["01"]["children_count"], 1)
        self.assertEqual(rows["01.01"]["appeals_count"], 1)

    def test_user_cannot_edit(self):
        self.login(self.user)
        self.assertEqual(self.client.post(self.URL, {"code": "9", "name": "X"}, format="json").status_code, 403)

    def test_delete_protected_when_used_or_has_children(self):
        section = AppealQuestion.objects.create(code="01", name="Bo'lim")
        used = AppealQuestion.objects.create(code="01.01", name="Savol", parent=section)
        free = AppealQuestion.objects.create(code="01.02", name="Bo'sh", parent=section)
        self.make_appeal(question=used)
        self.login(self.devonxona)
        self.assertEqual(self.client.delete(f"{self.URL}{section.id}/").status_code, 400)
        self.assertEqual(self.client.delete(f"{self.URL}{used.id}/").status_code, 400)
        self.assertEqual(self.client.delete(f"{self.URL}{free.id}/").status_code, 204)
        self.assertTrue(AppealQuestion.objects.filter(id=used.id).exists())

    def test_parent_cycle_rejected(self):
        a = AppealQuestion.objects.create(code="01", name="A")
        b = AppealQuestion.objects.create(code="01.01", name="B", parent=a)
        self.login(self.devonxona)
        resp = self.client.patch(f"{self.URL}{a.id}/", {"parent_id": b.id}, format="json")
        self.assertEqual(resp.status_code, 400)
        resp = self.client.patch(f"{self.URL}{a.id}/", {"is_active": False}, format="json")
        self.assertEqual(resp.status_code, 200)
