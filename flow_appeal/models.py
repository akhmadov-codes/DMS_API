"""
Og'zaki murojaatlar (jismoniy va yuridik shaxslarning murojaatlarini qayd etish kartochkasi).

Rezolyutsiya, bajarish muddati va ijrochilar mavjud Task orqali yuritiladi (Task.appeal).
Shu sababli ijro, javoblar, nazoratdan yechish va status mantig'i qayta yozilmaydi.
"""
from django.db import models, transaction
from django.utils import timezone

from flow_document.models import Sender, Signer
from flow_user.models import CustomUser, Department


# ---------- Ma'lumotnomalar (rasmiy tasniflagich) ----------
class AppealQuestion(models.Model):
    """Murojaatda ko'tarilgan savol - rasmiy tasniflagich (ierarxik: bo'lim -> savol)."""

    code = models.CharField(max_length=50, unique=True, verbose_name="Kod")
    name = models.CharField(max_length=500, verbose_name="Nomi")
    parent = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True, related_name="children")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["code"]
        verbose_name = "Savol (tasniflagich)"
        verbose_name_plural = "Savollar (tasniflagich)"

    def __str__(self):
        return f"{self.code} {self.name[:80]}"


class AppealForm(models.Model):
    """Murojaatning shakli: og'zaki, yozma, elektron."""

    name = models.CharField(max_length=255, unique=True)

    class Meta:
        ordering = ["id"]
        verbose_name = "Murojaat shakli"
        verbose_name_plural = "Murojaat shakllari"

    def __str__(self):
        return self.name


class AppealKind(models.Model):
    """Murojaatning turi: ariza, taklif, shikoyat."""

    name = models.CharField(max_length=255, unique=True)

    class Meta:
        ordering = ["id"]
        verbose_name = "Murojaat turi"
        verbose_name_plural = "Murojaat turlari"

    def __str__(self):
        return self.name


class ReceptionType(models.Model):
    """Qabul shakli: shaxsiy qabul, sayyor qabul, telefon orqali..."""

    name = models.CharField(max_length=255, unique=True)

    class Meta:
        ordering = ["id"]
        verbose_name = "Qabul shakli"
        verbose_name_plural = "Qabul shakllari"

    def __str__(self):
        return self.name


# ---------- Tartib raqami hisoblagichi ----------
class AppealCounter(models.Model):
    """Har yil uchun alohida tartib raqami (OM-2026/0001)."""

    year = models.PositiveIntegerField(primary_key=True)
    last = models.PositiveIntegerField(default=0)

    @classmethod
    def next_number(cls, year):
        """Tranzaksiya ichida chaqiriladi: qator qulflanadi, raqam takrorlanmaydi."""
        cls.objects.get_or_create(year=year)
        counter = cls.objects.select_for_update().get(year=year)
        counter.last += 1
        counter.save(update_fields=["last"])
        return counter.last


# ---------- Og'zaki murojaat ----------
class OralAppeal(models.Model):
    APPLICANT_INDIVIDUAL = "individual"
    APPLICANT_LEGAL = "legal"
    APPLICANT_CHOICES = [
        (APPLICANT_INDIVIDUAL, "Jismoniy shaxs"),
        (APPLICANT_LEGAL, "Yuridik shaxs"),
    ]
    NUMBER_PREFIX = "OM"

    # Tartib raqami (avtomatik)
    reg_year = models.PositiveIntegerField(editable=False, db_index=True)
    reg_seq = models.PositiveIntegerField(editable=False)
    reg_number = models.CharField(max_length=30, unique=True, editable=False, verbose_name="Tartib raqami")

    # 1-varaq: qayd etish kartochkasi
    question = models.ForeignKey(AppealQuestion, on_delete=models.SET_NULL, null=True, blank=True, related_name="appeals", verbose_name="Savol")
    applicant_type = models.CharField(max_length=20, choices=APPLICANT_CHOICES, default=APPLICANT_INDIVIDUAL)
    applicant_name = models.CharField(max_length=500, verbose_name="Murojaat qiluvchi")
    address = models.CharField(max_length=500, blank=True, default="", verbose_name="Manzili")
    phone = models.CharField(max_length=50, blank=True, default="")
    received_date = models.DateField(db_index=True, verbose_name="Murojaat kelib tushgan sana")
    appeal_form = models.ForeignKey(AppealForm, on_delete=models.SET_NULL, null=True, blank=True, related_name="appeals")
    reception_type = models.ForeignKey(ReceptionType, on_delete=models.SET_NULL, null=True, blank=True, related_name="appeals")
    appeal_kind = models.ForeignKey(AppealKind, on_delete=models.SET_NULL, null=True, blank=True, related_name="appeals")
    summary = models.TextField(blank=True, default="", verbose_name="Qisqacha mazmuni")
    signer = models.ForeignKey(Signer, on_delete=models.SET_NULL, null=True, blank=True, related_name="appeals", verbose_name="Rezolyutsiyani imzolagan rahbar")
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name="appeals", verbose_name="Tarkibiy bo'linma")

    # 2-varaq: ko'rib chiqish holati
    original_due_date = models.DateField(null=True, blank=True, verbose_name="Dastlabki muddat")
    extended_due_date = models.DateField(null=True, blank=True, verbose_name="Uzaytirilgan muddat")
    extended_by = models.ForeignKey(Signer, on_delete=models.SET_NULL, null=True, blank=True, related_name="extended_appeals", verbose_name="Muddatni uzaytirgan")
    extended_at = models.DateTimeField(null=True, blank=True)
    result_summary = models.TextField(blank=True, default="", verbose_name="Ko'rib chiqish natijalari")
    closed_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name="closed_appeals", verbose_name="Nazoratdan olgan")
    closed_at = models.DateTimeField(null=True, blank=True, verbose_name="Nazoratdan olingan sana")

    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name="appeals", verbose_name="Ro'yxatga olgan")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ("reg_year", "reg_seq")
        verbose_name = "Og'zaki murojaat"
        verbose_name_plural = "Og'zaki murojaatlar"

    def __str__(self):
        return f"{self.reg_number} - {self.applicant_name}"

    def save(self, *args, **kwargs):
        if not self.reg_number:
            with transaction.atomic():
                self.reg_year = timezone.localdate().year
                self.reg_seq = AppealCounter.next_number(self.reg_year)
                self.reg_number = f"{self.NUMBER_PREFIX}-{self.reg_year}/{self.reg_seq:04d}"
                super().save(*args, **kwargs)
            return
        super().save(*args, **kwargs)


class AppealForwarding(models.Model):
    """Murojaat boshqa tashkilotga yuborilgani va javob xati."""

    appeal = models.ForeignKey(OralAppeal, on_delete=models.CASCADE, related_name="forwardings")
    sent_date = models.DateField(verbose_name="Yuborilgan sana")
    sent_to = models.ForeignKey(Sender, on_delete=models.SET_NULL, null=True, blank=True, related_name="appeal_forwardings", verbose_name="Qayerga yuborilgan")
    reply_number = models.CharField(max_length=100, blank=True, default="", verbose_name="Javob xatining raqami")
    reply_date = models.DateField(null=True, blank=True, verbose_name="Javob xatining sanasi")
    reply_received_date = models.DateField(null=True, blank=True, verbose_name="Javob xati kelgan sana")
    note = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sent_date", "id"]
        verbose_name = "Yuborish"
        verbose_name_plural = "Yuborishlar"

    def __str__(self):
        return f"{self.appeal.reg_number} -> {self.sent_to or '?'}"
