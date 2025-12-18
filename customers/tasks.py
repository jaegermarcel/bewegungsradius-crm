"""
customers/tasks.py - Celery Tasks (Pure Wrapper)
==================================================
Tasks sind nur noch dünne Wrapper um Services
Alle Geschäftslogik ist in email_services/ (wartbar + testbar)
"""

from celery import shared_task
from django.utils import timezone
import logging

from .email_services.birthday_emails import BirthdayEmailService
from .email_services.discount_emails import DiscountCodeEmailService
from company.models import CompanyInfo

logger = logging.getLogger(__name__)


# ==================== DISCOUNT CODE TASKS ====================

@shared_task
def send_course_completion_emails():
    """Sendet Dankeschön-Mails für abgeschlossene Kurse"""
    try:
        service = DiscountCodeEmailService(CompanyInfo.get_solo())
        result = service.send_course_completion_emails()
        logger.info(f"✓ Rabattcode-Completion-Emails: {result}")
        return result
    except Exception as e:
        logger.error(f"❌ Fehler beim Versand von Completion-Emails: {e}")
        return {'sent': 0, 'errors': 1, 'error': str(e)}


@shared_task
def delete_old_discount_codes():
    """Löscht Rabattcodes älter als 13 Monate"""
    try:
        from customers.models import CustomerDiscountCode
        from dateutil.relativedelta import relativedelta

        cutoff_date = timezone.now() - relativedelta(months=13)
        count = CustomerDiscountCode.objects.filter(created_at__lt=cutoff_date).delete()[0]

        logger.info(f"✓ {count} alte Rabattcodes gelöscht")
        return {'deleted': count}
    except Exception as e:
        logger.error(f"❌ Fehler beim Löschen alter Codes: {e}")
        return {'deleted': 0, 'error': str(e)}


# ==================== BIRTHDAY EMAIL TASKS ====================

@shared_task
def check_and_send_birthday_emails():
    """
    ✅ Celery Task: Versendet Geburtstags-Emails für heute

    Wird täglich ausgeführt (z.B. um 08:00 Uhr)

    Prüft ob Kunden heute Geburtstag haben und versendet
    personalisierte Glückwunsch-Emails
    """
    try:
        logger.info("🎂 Starting birthday email check for today...")

        service = BirthdayEmailService(CompanyInfo.get_solo())
        result = service.send_birthday_emails_for_today()

        logger.info(
            f"✅ Birthday check abgeschlossen: "
            f"{result['sent']} versendet, {result['errors']} Fehler"
        )

        return result

    except Exception as e:
        logger.error(f"❌ Kritischer Fehler bei Geburtstagsprüfung: {e}")
        return {
            'sent': 0,
            'errors': 1,
            'failed': [{'error': str(e)}],
        }

