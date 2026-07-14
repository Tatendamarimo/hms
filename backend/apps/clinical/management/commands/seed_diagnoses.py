import csv
from pathlib import Path

from django.core.management.base import BaseCommand

from apps.clinical.models import Diagnosis

DATA_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "icd10_subset.csv"


class Command(BaseCommand):
    help = (
        "Seed/refresh the ICD-10 diagnosis catalog from the bundled subset "
        "(idempotent; names are updated in place, codes are never deleted — "
        "retire codes by setting is_active=False)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--file", default=str(DATA_FILE),
            help="CSV with 'code,name' header (defaults to the bundled subset)",
        )

    def handle(self, *args, **options):
        created = updated = 0
        with open(options["file"], newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                code, name = row["code"].strip(), row["name"].strip()
                diagnosis, was_created = Diagnosis.objects.get_or_create(
                    code=code, defaults={"name": name}
                )
                if was_created:
                    created += 1
                elif diagnosis.name != name:
                    diagnosis.name = name
                    diagnosis.save(update_fields=["name", "updated_at"])
                    updated += 1
        self.stdout.write(
            self.style.SUCCESS(f"Diagnoses seeded ({created} created, {updated} updated).")
        )
