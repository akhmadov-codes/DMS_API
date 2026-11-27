from django.contrib import admin

from .models import AppealForm, AppealForwarding, AppealKind, AppealQuestion, OralAppeal, ReceptionType


@admin.register(AppealQuestion)
class AppealQuestionAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "parent", "is_active")
    list_filter = ("is_active",)
    search_fields = ("code", "name")
    autocomplete_fields = ("parent",)


admin.site.register(AppealForm)
admin.site.register(AppealKind)
admin.site.register(ReceptionType)


class AppealForwardingInline(admin.TabularInline):
    model = AppealForwarding
    extra = 0


@admin.register(OralAppeal)
class OralAppealAdmin(admin.ModelAdmin):
    list_display = ("reg_number", "applicant_name", "received_date", "appeal_kind", "department")
    list_filter = ("reg_year", "appeal_form", "appeal_kind", "reception_type")
    search_fields = ("reg_number", "applicant_name", "summary")
    readonly_fields = ("reg_number", "reg_year", "reg_seq", "created_at", "updated_at")
    inlines = [AppealForwardingInline]
