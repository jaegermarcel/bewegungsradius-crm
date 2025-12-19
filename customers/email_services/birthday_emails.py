"""
customers/email_services/birthday_emails.py - Geburtstag Emails
==============================================================
✅ Erbt von BaseEmailService
✅ Spezialisiert auf Geburtstags-Emails
"""

import logging

from django.db.models.functions import ExtractDay, ExtractMonth
from django.utils import timezone

from bewegungsradius.core.email import (
    BaseEmailService,
    EmailPayload,
    EmailTemplateConfig,
)

logger = logging.getLogger(__name__)


class BirthdayInfo:
    """Value Object für Geburtstagsinformationen"""

    def __init__(self, customer):
        self.customer = customer
        self.today = timezone.now().date()

    @property
    def age(self) -> int:
        """Berechnet aktuelles Alter"""
        if not self.customer.birthday:
            return None

        today = self.today
        born = self.customer.birthday

        return (
            today.year - born.year - ((today.month, today.day) < (born.month, born.day))
        )


class BirthdayEmailService(BaseEmailService):
    """Service für Geburtstags-E-Mails"""

    TEMPLATE_PATH = "email/notifications/birthday_notification.html"

    def get_template_config(self, customer, **kwargs) -> EmailTemplateConfig:
        """Erstellt Template Config für Geburtstag"""
        birthday_info = BirthdayInfo(customer)

        context = {
            "customer": customer,
            "age": birthday_info.age,
            "company": self.company_info,
        }
        return EmailTemplateConfig(self.TEMPLATE_PATH, context)

    def build_email_payload(
        self, customer, html_content: str = None, **kwargs
    ) -> EmailPayload:
        """Erstellt Email Payload für Geburtstag"""
        subject = f"🎉 Alles Gute zum Geburtstag, {customer.first_name}!"

        return EmailPayload(
            subject=subject,
            html_content=html_content or "",
            recipient_email=customer.email,
            from_email=self.company_info.email if self.company_info else None,
        )

    def send_birthday_email(self, customer) -> bool:
        """Versendet Geburtstags-Email"""
        if not customer.email:
            raise ValueError(f"{customer.get_full_name()} hat keine E-Mail")
        if not customer.birthday:
            raise ValueError(f"Kein Geburtsdatum für {customer.get_full_name()}")

        return super().send_single_email(customer=customer)

    def get_customers_with_birthday_today(self):
        """Gibt Kunden mit Geburtstag heute zurück"""
        from customers.models import Customer

        today = timezone.now().date()
        return Customer.objects.filter(
            birthday__month=today.month, birthday__day=today.day
        ).exclude(birthday__isnull=True)

    def get_customers_with_birthday_in_days(self, days: int):
        """Gibt Kunden mit Geburtstag in X Tagen zurück"""
        from customers.models import Customer

        target_date = timezone.now().date() + timezone.timedelta(days=days)

        return (
            Customer.objects.annotate(
                birth_month=ExtractMonth("birthday"), birth_day=ExtractDay("birthday")
            )
            .filter(birth_month=target_date.month, birth_day=target_date.day)
            .exclude(birthday__isnull=True)
        )

    def send_birthday_emails_for_today(self) -> dict:
        """Versendet Emails für alle Geburtstage heute"""
        customers = self.get_customers_with_birthday_today()
        return self.send_bulk_emails([{"customer": c} for c in customers])

    def send_birthday_emails_for_days_ahead(self, days: int) -> dict:
        """Versendet Voraus-Benachrichtigungen"""
        customers = self.get_customers_with_birthday_in_days(days)
        return self.send_bulk_emails([{"customer": c} for c in customers])
