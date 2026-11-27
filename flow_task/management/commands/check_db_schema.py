"""
Deploydan oldin tekshiruv: real bazadagi jadvallar Django "qo'llangan" deb hisoblagan migratsiyalar
bilan mos keladimi va qaysi migratsiyalar qo'llanadi. Bazaga hech narsa yozmaydi.

    python manage.py check_db_schema

Natija:
  - "Qo'llanadigan migratsiyalar" - migrate nima qilishini ko'rsatadi
  - XATO     - migrate yoki ilova ishlashida muammo beradi (deploy qilmang)
  - OGOHLANTIRISH - ishlashga xalaqit bermaydi, lekin bilib qo'ygan ma'qul
"""
from django.core.management.base import BaseCommand
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

APPS = ("flow_user", "flow_document", "flow_task", "flow_taskres", "flow_appeal")


class Command(BaseCommand):
    help = "Bazaning tuzilishini migratsiyalar bilan solishtiradi (faqat o'qiydi)"

    def handle(self, *args, **options):
        executor = MigrationExecutor(connection)
        loader = executor.loader
        applied = set(loader.applied_migrations)

        # 1. Qo'llanadigan migratsiyalar
        plan = executor.migration_plan(loader.graph.leaf_nodes())
        self.stdout.write(self.style.MIGRATE_HEADING("Qo'llanadigan migratsiyalar:"))
        for migration, backwards in plan:
            self.stdout.write(f"  {'ORTGA ' if backwards else ''}{migration.app_label}.{migration.name}")
        if not plan:
            self.stdout.write("  (yo'q - baza oxirgi holatda)")

        # Bazada yozilgan, lekin kodda fayli yo'q migratsiyalar
        orphans = sorted(f"{a}.{n}" for a, n in applied if a in APPS and (a, n) not in loader.disk_migrations)
        errors, warnings = [], []
        for name in orphans:
            warnings.append(f"Bazada qo'llangan, lekin kodda fayli yo'q migratsiya: {name}")

        # 2. Hozir qo'llangan migratsiyalar bo'yicha kutilgan tuzilish va real baza
        state = loader.project_state(sorted(n for n in applied if n in loader.graph.nodes))
        with connection.cursor() as cursor:
            tables = set(connection.introspection.table_names(cursor))
            for model in state.apps.get_models():
                if model._meta.app_label not in APPS or not model._meta.managed:
                    continue
                table = model._meta.db_table
                if table not in tables:
                    errors.append(f"{table}: jadval bazada yo'q (migratsiya qo'llangan deb yozilgan)")
                    continue
                columns = {c.name: c for c in connection.introspection.get_table_description(cursor, table)}
                expected = set()
                for field in model._meta.local_fields:
                    column = field.column
                    expected.add(column)
                    info = columns.get(column)
                    if info is None:
                        errors.append(f"{table}.{column}: ustun bazada yo'q")
                        continue
                    if field.null and not info.null_ok:
                        errors.append(f"{table}.{column}: modelda bo'sh bo'lishi mumkin, bazada NOT NULL")
                    elif not field.null and info.null_ok and not field.primary_key:
                        warnings.append(f"{table}.{column}: modelda majburiy, bazada NULL ruxsat")
                    max_length = getattr(field, "max_length", None)
                    size = getattr(info, "internal_size", None) or getattr(info, "display_size", None)
                    if max_length and size and size > 0 and size < max_length:
                        warnings.append(f"{table}.{column}: bazada {size} belgi, modelda {max_length}")
                # Modelda yo'q, bazada NOT NULL ustun - yangi yozuv qo'shishda xato beradi
                for name, info in columns.items():
                    if name not in expected and not info.null_ok and info.default is None:
                        errors.append(f"{table}.{name}: modelda yo'q, bazada NOT NULL va default'siz")
                    elif name not in expected:
                        warnings.append(f"{table}.{name}: bazada ortiqcha ustun (modelda yo'q)")

        # 3. Natija
        self.stdout.write("")
        for msg in warnings:
            self.stdout.write(self.style.WARNING(f"OGOHLANTIRISH  {msg}"))
        for msg in errors:
            self.stdout.write(self.style.ERROR(f"XATO  {msg}"))
        if errors:
            self.stdout.write(self.style.ERROR(f"\n{len(errors)} ta xato. migrate qilmang - natijani dasturchiga yuboring."))
        else:
            self.stdout.write(self.style.SUCCESS("\nBaza tuzilishi migratsiyalar bilan mos. migrate xavfsiz."))
