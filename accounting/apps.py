from django.apps import AppConfig


class AccountingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounting'
    verbose_name = 'Accounting & Finanzen'

    def ready(self):
        """Registriere Signals wenn App geladen wird"""
        import accounting.models  # noqa