"""Boshlang'ich ma'lumotnoma qiymatlari. Admin paneldan tahrirlash mumkin."""
from django.db import migrations

FORMS = ["Og'zaki", "Yozma", "Elektron"]
KINDS = ["Ariza", "Taklif", "Shikoyat"]
RECEPTION_TYPES = ["Shaxsiy qabul", "Sayyor qabul", "Ishonch telefoni orqali", "Videoaloqa orqali"]


def seed(apps, schema_editor):
    for model_name, names in (("AppealForm", FORMS), ("AppealKind", KINDS), ("ReceptionType", RECEPTION_TYPES)):
        model = apps.get_model("flow_appeal", model_name)
        for name in names:
            model.objects.get_or_create(name=name)


class Migration(migrations.Migration):
    dependencies = [("flow_appeal", "0001_initial")]

    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
