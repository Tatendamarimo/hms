from django.contrib import admin

from .models import ServiceItem, ServicePrice


class ServicePriceInline(admin.TabularInline):
    model = ServicePrice
    extra = 0
    can_delete = False
    readonly_fields = ("created_at", "created_by")

    def has_change_permission(self, request, obj=None):
        return False  # price history is append-only


@admin.register(ServiceItem)
class ServiceItemAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "type", "clinic", "is_active")
    list_filter = ("clinic", "type", "is_active")
    search_fields = ("code", "name")
    inlines = [ServicePriceInline]
