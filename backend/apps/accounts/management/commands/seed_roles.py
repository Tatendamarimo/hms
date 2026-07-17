from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand

from apps.accounts import roles
from apps.accounts.roles import ALL_ROLES

# Module-level permissions grow per phase; group membership stays the single
# source of truth for who can do what beyond the role_map defaults.
ROLE_PERMISSIONS = {
    roles.CASHIER: [
        ("encounters", "close_with_balance"),
        ("billing", "reverse_payment"),
    ],
    # apply_discount is deliberately Admin-only by default (fraud surface);
    # a clinic that trusts Cashiers with discounts grants it explicitly.
    roles.ADMIN: [
        ("encounters", "close_with_balance"),
        ("billing", "apply_discount"),
        ("billing", "reverse_payment"),
    ],
}


class Command(BaseCommand):
    help = "Create the FRD §3 role groups and their permissions (idempotent)."

    def handle(self, *args, **options):
        created_count = 0
        for name in ALL_ROLES:
            group, created = Group.objects.get_or_create(name=name)
            if created:
                created_count += 1
                self.stdout.write(f"Created role: {name}")
            for app_label, codename in ROLE_PERMISSIONS.get(name, []):
                permission = Permission.objects.get(
                    content_type__app_label=app_label, codename=codename
                )
                group.permissions.add(permission)
        self.stdout.write(
            self.style.SUCCESS(
                f"Roles ready ({created_count} created, {len(ALL_ROLES) - created_count} existing)."
            )
        )
