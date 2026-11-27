"""
Savollar tasniflagichini CSV fayldan yuklash.

Fayl ustunlari (sarlavha qatori bilan, ajratuvchi ";" yoki ","):
    code;name;parent_code
parent_code bo'sh bo'lsa - yuqori darajadagi bo'lim. Mavjud kodlar yangilanadi, yangilari qo'shiladi.

    python manage.py import_appeal_questions savollar.csv
"""
from django.core.management.base import BaseCommand, CommandError

from flow_appeal.importing import ImportError_, decode_bytes, import_questions, parse_rows


class Command(BaseCommand):
    help = "Murojaat savollari tasniflagichini CSV fayldan yuklaydi"

    def add_arguments(self, parser):
        parser.add_argument("path")

    def handle(self, path, **options):
        try:
            with open(path, "rb") as fh:
                result = import_questions(parse_rows(decode_bytes(fh.read())))
        except FileNotFoundError:
            raise CommandError(f"Fayl topilmadi: {path}")
        except ImportError_ as exc:
            raise CommandError(str(exc))
        self.stdout.write(self.style.SUCCESS(f"Qo'shildi: {result['created']}, yangilandi: {result['updated']}"))
