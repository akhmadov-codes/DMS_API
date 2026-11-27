"""
Savollar tasniflagichini CSV matndan yuklash (management buyrug'i va API uchun umumiy).

Ustunlar (sarlavha qatori bilan, ajratuvchi ";" yoki ","):
    code;name;parent_code[;is_active]
parent_code bo'sh bo'lsa - yuqori darajadagi bo'lim. Mavjud kodlar yangilanadi, yangilari qo'shiladi.
"""
import csv
import io

from django.db import transaction

from .models import AppealQuestion


class ImportError_(Exception):
    """Fayl tuzilishidagi xato (foydalanuvchiga ko'rsatiladi)."""


class _Semicolon(csv.excel):
    delimiter = ";"


def decode_bytes(raw: bytes) -> str:
    # Excel ko'pincha UTF-8 (BOM bilan) yoki Windows-1251 da saqlaydi
    for enc in ("utf-8-sig", "cp1251"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    raise ImportError_("Fayl kodirovkasi aniqlanmadi. CSV faylni UTF-8 da saqlang.")


def parse_rows(text: str) -> list[dict]:
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=";,")
    except csv.Error:
        dialect = _Semicolon
    rows = list(csv.DictReader(io.StringIO(text), dialect=dialect))
    headers = {(h or "").strip().lower() for h in (rows[0].keys() if rows else [])}
    missing = {"code", "name"} - headers
    if missing:
        raise ImportError_(f"Ustunlar yetishmaydi: {', '.join(sorted(missing))}")
    # Sarlavhalardagi bo'shliq / katta harflar e'tiborsiz qoldiriladi
    return [{(k or "").strip().lower(): (v or "").strip() for k, v in row.items()} for row in rows]


@transaction.atomic
def import_questions(rows: list[dict]) -> dict:
    created = updated = 0
    by_code = {}
    for row in rows:
        code, name = row.get("code", ""), row.get("name", "")
        if not code or not name:
            continue
        defaults = {"name": name}
        # Ixtiyoriy ustun (eksport faylida bor): 1/0, ha/yo'q
        active = row.get("is_active", "").lower()
        if active:
            defaults["is_active"] = active not in ("0", "false", "yo'q", "нет", "no")
        obj, is_new = AppealQuestion.objects.update_or_create(code=code, defaults=defaults)
        by_code[code] = (obj, row.get("parent_code", ""))
        created += is_new
        updated += not is_new
    # Ota-bo'limlar barcha qatorlar yozilgandan keyin bog'lanadi (tartib muhim emas)
    for code, (obj, parent_code) in by_code.items():
        parent = None
        if parent_code:
            if parent_code == code:
                raise ImportError_(f"{code}: o'zi o'ziga ota-bo'lim bo'la olmaydi")
            parent = by_code.get(parent_code, (None,))[0] or AppealQuestion.objects.filter(code=parent_code).first()
            if parent is None:
                raise ImportError_(f"{code}: ota-bo'lim topilmadi ({parent_code})")
        if obj.parent_id != (parent.id if parent else None):
            obj.parent = parent
            obj.save(update_fields=["parent"])
    # Halqa (A -> B -> A) bo'lsa butun import bekor qilinadi (tranzaksiya)
    parents = dict(AppealQuestion.objects.values_list("id", "parent_id"))
    for obj, _ in by_code.values():
        seen, node = set(), obj.id
        while node is not None:
            if node in seen:
                raise ImportError_(f"{obj.code}: ota-bo'limlar halqa hosil qilmoqda")
            seen.add(node)
            node = parents.get(node)
    return {"created": created, "updated": updated}
