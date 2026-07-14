from django.contrib import admin

from .models import Encounter


@admin.register(Encounter)
class EncounterAdmin(admin.ModelAdmin):
    """Read-only oversight: status changes must go through the state machine
    (API), never the admin."""

    list_display = ("patient", "type", "status", "arrived_at", "assigned_doctor", "clinic")
    list_filter = ("clinic", "status", "type")
    date_hierarchy = "arrived_at"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
