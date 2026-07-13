from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = "apps.core"
    label = "core"

    def ready(self):
        from . import audit

        audit.register_audited_models()
        audit.connect_auth_signals()
