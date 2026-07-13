from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from apps.accounts.roles import ALL_ROLES


class Command(BaseCommand):
    help = "Create the FRD §3 role groups (idempotent)."

    def handle(self, *args, **options):
        created_count = 0
        for name in ALL_ROLES:
            _, created = Group.objects.get_or_create(name=name)
            if created:
                created_count += 1
                self.stdout.write(f"Created role: {name}")
        self.stdout.write(
            self.style.SUCCESS(
                f"Roles ready ({created_count} created, {len(ALL_ROLES) - created_count} existing)."
            )
        )
