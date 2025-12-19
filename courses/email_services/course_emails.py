"""
courses/email_services/course_emails.py - Kurs-E-Mails
=====================================================
✅ NEUE DATEI: Course Start + Completion Emails
✅ Erbt von BaseEmailService
✅ Spezialisiert auf Kurs-Emails
"""

import logging

from bewegungsradius.core.email import (BaseEmailService, EmailPayload,
                                        EmailTemplateConfig)

logger = logging.getLogger(__name__)


# ==================== SERVICES ====================


class DiscountCodeRepository:
    """Repository für Rabattcode-Datenbankoperationen"""

    def find_active_for_course_and_customer(self, course, customer):
        """Sucht aktiven Rabattcode für Kurs und Kunde"""
        from customers.models import CustomerDiscountCode

        return CustomerDiscountCode.objects.filter(
            course=course, customer=customer, status__in=["planned", "sent"]
        ).first()


class DiscountCodeService:
    """Service für Rabattcode-Logik"""

    def __init__(self, repository=None):
        self.repository = repository or DiscountCodeRepository()

    def get_discount_code_for_participant(self, course, customer):
        """Holt Rabattcode für Teilnehmer"""
        try:
            discount_code = self.repository.find_active_for_course_and_customer(
                course, customer
            )

            if discount_code:
                logger.info(f"✓ Rabattcode gefunden: {discount_code.code}")
                return discount_code
            else:
                logger.debug(
                    f"Kein Rabattcode für Kurs {course.id} und Kunde {customer.id}"
                )
                return None

        except Exception as e:
            logger.error(f"Fehler beim Laden des Rabattcodes: {e}")
            return None


# ==================== EMAIL SERVICES ====================


class CourseStartEmailService(BaseEmailService):
    """Service für Kurs-Start-Notifications"""

    TEMPLATE_PATH = "email/notifications/course_start_email.html"

    def get_template_config(self, course, customer, **kwargs) -> EmailTemplateConfig:
        """Erstellt Template Config für Kurs-Start"""
        context = {
            "customer": customer,
            "course": course,
            "company": self.company_info,
        }
        return EmailTemplateConfig(self.TEMPLATE_PATH, context)

    def build_email_payload(
        self, course, customer, html_content: str = None, **kwargs
    ) -> EmailPayload:
        """Erstellt Email Payload"""
        subject = f"Kurs startet bald: {course.offer.title}"

        return EmailPayload(
            subject=subject,
            html_content=html_content or "",
            recipient_email=customer.email,
            from_email=self.company_info.email if self.company_info else None,
        )

    def send_course_start_email(self, course):
        """Versendet Start-Email an alle Teilnehmer"""
        participants = list(course.participants_inperson.all()) + list(
            course.participants_online.all()
        )

        return self.send_bulk_emails(
            [{"course": course, "customer": p} for p in participants]
        )


class CourseCompletionEmailService(BaseEmailService):
    """Service für Kurs-Completion-Notifications

    ✅ Lädt Rabattcode für Teilnehmer
    """

    TEMPLATE_PATH = "email/notifications/course_completion_email.html"

    def __init__(self, company_info=None, discount_service=None):
        super().__init__(company_info)
        self.discount_service = discount_service or DiscountCodeService()

    def get_template_config(self, course, customer, **kwargs) -> EmailTemplateConfig:
        """Erstellt Template Config für Kurs-Ende"""
        discount_code = self.discount_service.get_discount_code_for_participant(
            course, customer
        )

        context = {
            "customer": customer,
            "course": course,
            "discount_code": discount_code,
            "company": self.company_info,
        }
        return EmailTemplateConfig(self.TEMPLATE_PATH, context)

    def build_email_payload(
        self, course, customer, html_content: str = None, **kwargs
    ) -> EmailPayload:
        """Erstellt Email Payload"""
        subject = f"Glückwunsch zum Abschluss: {course.offer.title}"

        return EmailPayload(
            subject=subject,
            html_content=html_content or "",
            recipient_email=customer.email,
            from_email=self.company_info.email if self.company_info else None,
        )

    def send_course_completion_email(self, course):
        """Versendet Completion-Email an alle Teilnehmer"""
        participants = list(course.participants_inperson.all()) + list(
            course.participants_online.all()
        )

        return self.send_bulk_emails(
            [{"course": course, "customer": p} for p in participants]
        )
