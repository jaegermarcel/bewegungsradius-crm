"""
customers/birthday_service.py - Business Logic für Geburtstags-E-Mails
=====================================================================
Service für Geburtstagserkennung und E-Mail-Versand
Unabhängig von Celery/Django Admin - Pure Business Logic

✅ NUR Glückwünsche - KEIN Rabattcode!
"""

import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone

logger = logging.getLogger(__name__)


# ==================== EXCEPTION CLASSES ====================


class BirthdayEmailError(Exception):
    """Fehler beim Geburtstags-Email-Versand"""


class BirthdayCheckError(BirthdayEmailError):
    """Fehler beim Geburtstagsprüfung"""


# ==================== REPOSITORIES ====================


class CustomerRepository:
    """Repository für Customer-Datenzugriff"""

    def __init__(self):
        from .models import Customer

        self.Customer = Customer

    def get_customers_with_birthday_today(self):
        """Gibt alle Kunden mit Geburtstag heute zurück"""
        today = timezone.now().date()

        try:
            customers = self.Customer.objects.filter(
                birthday__month=today.month, birthday__day=today.day
            ).exclude(birthday__isnull=True)

            logger.info(f"✓ {customers.count()} Kunden mit Geburtstag heute gefunden")
            return list(customers)

        except Exception as e:
            logger.error(f"Fehler beim Abrufen von Geburtstagskunden: {e}")
            raise BirthdayCheckError(f"Datenbankabfrage fehlgeschlagen: {e}")

    def get_customers_with_birthday_in_days(self, days: int):
        """Gibt Kunden mit Geburtstag in X Tagen zurück"""
        try:
            from django.db.models.functions import ExtractDay, ExtractMonth

            target_date = timezone.now().date() + timezone.timedelta(days=days)

            customers = (
                self.Customer.objects.annotate(
                    birth_month=ExtractMonth("birthday"),
                    birth_day=ExtractDay("birthday"),
                )
                .filter(birth_month=target_date.month, birth_day=target_date.day)
                .exclude(birthday__isnull=True)
            )

            logger.info(
                f"✓ {customers.count()} Kunden mit Geburtstag in {days} Tagen gefunden"
            )
            return list(customers)

        except Exception as e:
            logger.error(
                f"Fehler beim Abrufen von Geburtstagskunden in {days} Tagen: {e}"
            )
            raise BirthdayCheckError(f"Datenbankabfrage fehlgeschlagen: {e}")


# ==================== VALUE OBJECTS ====================


class BirthdayInfo:
    """Hält Geburtstagsinformationen"""

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

    @property
    def is_birthday_today(self) -> bool:
        """Prüft ob heute Geburtstag ist"""
        if not self.customer.birthday:
            return False

        today = self.today
        born = self.customer.birthday

        return (today.month, today.day) == (born.month, born.day)

    def __repr__(self):
        return f"BirthdayInfo({self.customer.get_full_name()}, age={self.age})"


class BirthdayEmailResult:
    """Hält Ergebnis eines Email-Versands"""

    def __init__(self):
        self.sent_count = 0
        self.error_count = 0
        self.failed_customers = []

    def add_sent(self):
        """Erhöht Versand-Zähler"""
        self.sent_count += 1

    def add_error(self, customer_name: str, error_msg: str):
        """Registriert Fehler"""
        self.error_count += 1
        self.failed_customers.append({"name": customer_name, "error": error_msg})

    def to_dict(self):
        """Konvertiert zu Dictionary"""
        return {
            "sent": self.sent_count,
            "errors": self.error_count,
            "failed": self.failed_customers,
            "total": self.sent_count + self.error_count,
        }

    def __repr__(self):
        return f"BirthdayEmailResult(sent={self.sent_count}, errors={self.error_count})"


# ==================== SERVICES ====================


class BirthdayTemplateService:
    """Service für Template-Rendering"""

    BIRTHDAY_TEMPLATE = "email/notifications/birthday_notification.html"

    def __init__(self, company_info):
        self.company_info = company_info

    def render_birthday_email(self, customer, age: int) -> str:
        """Rendert Geburtstags-Email-Template"""
        try:
            return render_to_string(
                self.BIRTHDAY_TEMPLATE,
                {
                    "customer": customer,
                    "age": age,
                    "company": self.company_info,
                },
            )
        except Exception as e:
            logger.error(f"Template-Rendering fehlgeschlagen: {e}")
            raise BirthdayEmailError(f"Template-Rendering fehlgeschlagen: {e}")

    def build_subject(self, customer, age: int) -> str:
        """Erstellt Email-Betreffzeile"""
        return f"🎉 Alles Gute zum Geburtstag, {customer.first_name}!"


class BirthdayEmailSender:
    """Service für Email-Versand - Single Responsibility"""

    def __init__(self, company_info):
        self.company_info = company_info
        self.template_service = BirthdayTemplateService(company_info)

    def send_birthday_email(self, customer) -> bool:
        """Sendet Geburtstags-Email an einen Kunden"""
        # Validiere Email
        if not customer.email:
            raise BirthdayEmailError(
                f"Kunde {customer.get_full_name()} hat keine Email-Adresse"
            )

        # Validiere Geburtsdatum
        if not customer.birthday:
            raise BirthdayEmailError(
                f"Kein Geburtsdatum für {customer.get_full_name()}"
            )

        # Erstelle BirthdayInfo
        birthday_info = BirthdayInfo(customer)

        # Rendere Template
        html_content = self.template_service.render_birthday_email(
            customer, birthday_info.age
        )

        # Erstelle Subject
        subject = self.template_service.build_subject(customer, birthday_info.age)

        # Versende Email
        self._send_email(subject, html_content, customer.email)

        logger.info(f"✓ Geburtstags-Email versendet an {customer.get_full_name()}")
        return True

    def send_bulk_birthday_emails(self, customers: list) -> BirthdayEmailResult:
        """Sendet Mails an mehrere Kunden"""
        result = BirthdayEmailResult()

        for customer in customers:
            try:
                self.send_birthday_email(customer)
                result.add_sent()
            except BirthdayEmailError as e:
                result.add_error(customer.get_full_name(), str(e))
                logger.error(f"❌ Fehler für {customer.get_full_name()}: {e}")
            except Exception as e:
                result.add_error(customer.get_full_name(), str(e))
                logger.error(
                    f"❌ Unerwarteter Fehler für {customer.get_full_name()}: {e}"
                )

        return result

    def _send_email(self, subject: str, html_content: str, to_email: str):
        """Versendet Email"""
        from_email = self.company_info.email or settings.DEFAULT_FROM_EMAIL

        email = EmailMultiAlternatives(
            subject=subject,
            body="Bitte verwende den HTML-Content",
            from_email=from_email,
            to=[to_email],
        )
        email.attach_alternative(html_content, "text/html")
        email.send()


class BirthdayCheckService:
    """Service für Geburtstagsprüfung - Orchestriert alles"""

    def __init__(self, company_info):
        self.company_info = company_info
        self.repository = CustomerRepository()
        self.sender = BirthdayEmailSender(company_info)

    def send_birthday_emails_for_today(self) -> BirthdayEmailResult:
        """Versendet Geburtstags-Emails für heute"""
        try:
            customers = self.repository.get_customers_with_birthday_today()

            if not customers:
                logger.info("ℹ️  Keine Geburtstage heute")
                return BirthdayEmailResult()

            logger.info(f"🎉 Versende Geburtstags-Emails an {len(customers)} Kunden...")
            result = self.sender.send_bulk_birthday_emails(customers)

            return result

        except BirthdayCheckError as e:
            logger.error(f"Fehler bei Geburtstagsprüfung: {e}")
            raise

    def send_birthday_emails_for_days_ahead(self, days: int) -> BirthdayEmailResult:
        """Versendet Voraus-Benachrichtigungen für Geburtstage in X Tagen"""
        try:
            customers = self.repository.get_customers_with_birthday_in_days(days)

            if not customers:
                logger.info(f"ℹ️  Keine Geburtstage in {days} Tagen")
                return BirthdayEmailResult()

            logger.info(
                f"📅 Versende Voraus-Benachrichtigungen an {len(customers)} Kunden..."
            )
            result = self.sender.send_bulk_birthday_emails(customers)

            return result

        except BirthdayCheckError as e:
            logger.error(f"Fehler bei Geburtstagsprüfung: {e}")
            raise


# ==================== LOGGER ====================


class BirthdayLogger:
    """Service für Logging - Single Responsibility"""

    @staticmethod
    def log_start(event_type: str) -> None:
        """Loggt Start"""
        logger.info(f"🎂 Starting birthday email check: {event_type}")

    @staticmethod
    def log_result(result: BirthdayEmailResult) -> None:
        """Loggt Ergebnis"""
        logger.info(
            f"✅ Geburtstags-Email Versand abgeschlossen: "
            f"{result.sent_count} versendet, "
            f"{result.error_count} Fehler"
        )

    @staticmethod
    def log_error(error: Exception) -> None:
        """Loggt Fehler"""
        logger.error(f"❌ Kritischer Fehler: {error}", exc_info=True)
