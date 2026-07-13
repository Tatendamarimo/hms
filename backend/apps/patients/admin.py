from django.contrib import admin

from .models import Patient


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    """Demographics only — allergies/conditions are managed through the
    clinical API where actions are role-gated and audited."""

    list_display = ("mrn", "last_name", "first_name", "date_of_birth", "clinic", "status")
    list_filter = ("clinic", "status")
    search_fields = ("mrn", "last_name", "first_name", "national_id", "phone")
    readonly_fields = ("mrn", "consent_given_at", "consent_captured_by")

    def has_delete_permission(self, request, obj=None):
        return False
