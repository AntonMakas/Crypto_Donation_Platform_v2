from django.apps import AppConfig


class JarsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name  = "apps.jars"
    label = "jars"
    verbose_name = "Fundraising Jars"

    def ready(self):
        import apps.jars.signals  # noqa: F401
