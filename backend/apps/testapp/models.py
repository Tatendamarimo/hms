"""Concrete model for exercising the core base-model contracts in tests.
This app is installed ONLY under config.settings.test — it never ships."""

from django.db import models

from apps.core.models import AuditedModel, ClinicScopedModel, SoftDeleteModel, TimeStampedModel


class Record(AuditedModel, ClinicScopedModel, SoftDeleteModel, TimeStampedModel):
    name = models.CharField(max_length=100)
    notes = models.TextField(blank=True)

    def __str__(self):
        return self.name
