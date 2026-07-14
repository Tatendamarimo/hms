from django.contrib import admin

from .models import Consultation, Diagnosis


@admin.register(Diagnosis)
class DiagnosisAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "is_active")
    search_fields = ("code", "name")
    list_filter = ("is_active",)


@admin.register(Consultation)
class ConsultationAdmin(admin.ModelAdmin):
    """Read-only oversight — clinical documents are only ever touched through
    the service layer, and signed ones not at all."""

    list_display = ("encounter", "doctor", "status", "version", "signed_at", "clinic")
    list_filter = ("clinic", "status")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
