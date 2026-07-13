from django.apps import AppConfig


class TestAppConfig(AppConfig):
    name = "apps.testapp"
    label = "testapp"
    verbose_name = "Test-only concrete models"
