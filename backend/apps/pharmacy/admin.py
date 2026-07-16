from django.contrib import admin

from .models import Medication


@admin.register(Medication)
class MedicationAdmin(admin.ModelAdmin):
    list_display = ("name", "strength", "form", "clinic", "is_active")
    list_filter = ("clinic", "form", "is_active")
    search_fields = ("name",)
