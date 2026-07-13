from django.core.management.base import BaseCommand, CommandError

from apps.billing.models import ServiceItem
from apps.clinics.models import Clinic

DEFAULT_SERVICES = [
    ("consult-general", "General Consultation", ServiceItem.Type.CONSULTATION),
    ("consult-followup", "Follow-up Review", ServiceItem.Type.CONSULTATION),
    ("proc-dressing", "Wound Dressing", ServiceItem.Type.PROCEDURE),
    ("proc-injection", "Injection Administration", ServiceItem.Type.PROCEDURE),
]


class Command(BaseCommand):
    help = (
        "Seed the default service catalog for a clinic (idempotent). "
        "Prices are deliberately NOT seeded — they are clinic business data "
        "set by the Admin via the price list."
    )

    def add_arguments(self, parser):
        parser.add_argument("clinic_code", help="Clinic code to seed")

    def handle(self, *args, **options):
        try:
            clinic = Clinic.objects.get(code=options["clinic_code"])
        except Clinic.DoesNotExist as exc:
            raise CommandError(f"No clinic with code '{options['clinic_code']}'") from exc

        created = 0
        for code, name, service_type in DEFAULT_SERVICES:
            _, was_created = ServiceItem.objects.get_or_create(
                clinic=clinic, code=code, defaults={"name": name, "type": service_type}
            )
            created += was_created
        self.stdout.write(
            self.style.SUCCESS(f"Catalog ready for {clinic.name} ({created} services created).")
        )
