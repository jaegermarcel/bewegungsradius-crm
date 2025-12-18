"""
customers/email_services/discount_emails.py - Rabattcode Emails
===============================================================
✅ Erbt von BaseEmailService
✅ Spezialisiert auf Rabattcodes
✅ Single Responsibility
"""

from django.utils import timezone
from bewegungsradius.core.email import BaseEmailService, EmailPayload, EmailTemplateConfig
import logging

logger = logging.getLogger(__name__)


class DiscountCodeEmailService(BaseEmailService):
    """Service für Rabattcode-E-Mails"""

    TEMPLATE_PATH = 'email/notifications/discount_notification.html'

    def get_template_config(self, customer, discount_code, **kwargs) -> EmailTemplateConfig:
        """Erstellt Template Config für Rabattcode"""
        context = {
            'customer': customer,
            'discount_code': discount_code,
            'company': self.company_info,
        }
        return EmailTemplateConfig(self.TEMPLATE_PATH, context)

    def build_email_payload(
            self,
            customer,
            discount_code,
            html_content: str = None,
            **kwargs
    ) -> EmailPayload:
        """Erstellt Email Payload für Rabattcode"""
        subject = self._build_subject(discount_code)

        return EmailPayload(
            subject=subject,
            html_content=html_content or "",
            recipient_email=customer.email,
            from_email=self.company_info.email if self.company_info else None
        )

    def send_single_email(self, discount_code, customer=None):
        """Überschreibt Basis-Methode für bessere API"""
        if customer is None:
            customer = discount_code.customer

        if not customer.email:
            raise ValueError(f"{customer.get_full_name()} hat keine E-Mail")

        super().send_single_email(customer=customer, discount_code=discount_code)

        # Update Status
        discount_code.status = 'sent'
        discount_code.email_sent_at = timezone.now()
        discount_code.save()

    def send_bulk_emails(self, discount_codes: list) -> dict:
        """Versendet Emails für mehrere Rabattcodes"""
        result = {'sent': 0, 'errors': 0, 'failed': []}

        for code in discount_codes:
            try:
                self.send_single_email(code)
                result['sent'] += 1
            except Exception as e:
                result['errors'] += 1
                result['failed'].append({
                    'customer': code.customer.get_full_name(),
                    'error': str(e)
                })

        return result

    def send_course_completion_emails(self) -> dict:
        """Versendet Completion-Emails nach Kurs-Ende"""
        from courses.models import Course
        from customers.models import CustomerDiscountCode

        courses = Course.objects.filter(end_date=timezone.now().date())
        result = {'sent': 0, 'errors': 0}

        for course in courses:
            participants = list(course.participants_inperson.all()) + list(course.participants_online.all())

            for customer in participants:
                code = CustomerDiscountCode.objects.filter(
                    customer=customer,
                    course=course,
                    status='planned'
                ).first()

                if code:
                    try:
                        self.send_single_email(code)
                        result['sent'] += 1
                    except Exception:
                        result['errors'] += 1

        return result

    def _build_subject(self, discount_code) -> str:
        """Erstellt Subject-Zeile"""
        if discount_code.discount_type == 'percentage':
            discount_text = f'{int(discount_code.discount_value)}%'
        else:
            discount_text = f'{discount_code.discount_value:.2f}€'

        company_name = self.company_info.name if self.company_info else "Unternehmen"
        return f'Dein {discount_text} Rabattcode für {company_name}'