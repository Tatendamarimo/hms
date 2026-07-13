from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    fieldsets = DjangoUserAdmin.fieldsets + (("Contact", {"fields": ("phone",)}),)
    list_display = ("username", "first_name", "last_name", "phone", "is_active")
    search_fields = ("username", "first_name", "last_name", "phone")
