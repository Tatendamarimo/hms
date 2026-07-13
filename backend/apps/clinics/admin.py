from django.contrib import admin

from .models import Clinic, ClinicMembership


@admin.register(Clinic)
class ClinicAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "phone", "is_active")
    search_fields = ("name", "code")
    prepopulated_fields = {"code": ("name",)}


@admin.register(ClinicMembership)
class ClinicMembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "clinic", "is_active")
    list_filter = ("clinic", "is_active")
    search_fields = ("user__username",)
    autocomplete_fields = ("user",)
