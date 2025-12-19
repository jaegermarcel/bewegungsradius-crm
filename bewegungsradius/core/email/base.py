"""
core/email/base.py - Abstrakte E-Mail Basis-Klasse
==================================================
✅ DRY Prinzip: Vermeidet Code-Duplikation
✅ OOP: Vererbung für spezialisierte Services
✅ Single Responsibility: Nur Email-Versand-Logik
"""

import logging
from abc import ABC, abstractmethod

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


# ==================== VALUE OBJECTS ====================


class EmailTemplateConfig:
    """Template-Konfiguration - Value Object"""

    def __init__(self, template_path: str, template_context: dict):
        self.template_path = template_path
        self.context = template_context

    def render(self) -> str:
        """Rendert Template zu HTML"""
        from .exceptions import EmailTemplateRenderError

        try:
            return render_to_string(self.template_path, self.context)
        except Exception as e:
            logger.error(
                f"Template Rendering fehlgeschlagen ({self.template_path}): {e}"
            )
            raise EmailTemplateRenderError(
                f"Template konnte nicht gerendert werden: {e}"
            )


class EmailPayload:
    """E-Mail Payload - Value Object"""

    def __init__(
        self,
        subject: str,
        html_content: str,
        recipient_email: str,
        from_email: str = None,
    ):
        self.subject = subject
        self.html_content = html_content
        self.recipient_email = recipient_email
        self.from_email = from_email or settings.DEFAULT_FROM_EMAIL

    def validate(self):
        """Validiert Payload"""
        from .exceptions import EmailValidationError

        if not self.subject:
            raise EmailValidationError("Subject ist erforderlich")
        if not self.html_content:
            raise EmailValidationError("HTML-Content ist erforderlich")
        if not self.recipient_email:
            raise EmailValidationError("Recipient Email ist erforderlich")


# ==================== BASE SERVICE ====================


class BaseEmailService(ABC):
    """Abstrakte Basis-Klasse für alle E-Mail Services

    Implementiert:
    - Template Rendering
    - Email Versand (EmailMultiAlternatives)
    - Error Handling
    - Logging

    Subklassen müssen implementieren:
    - build_email_payload()
    - get_template_config()
    """

    def __init__(self, company_info=None):
        self.company_info = company_info

    @abstractmethod
    def build_email_payload(self, *args, **kwargs) -> EmailPayload:
        """Muss von Subklasse implementiert werden"""

    @abstractmethod
    def get_template_config(self, *args, **kwargs) -> EmailTemplateConfig:
        """Muss von Subklasse implementiert werden"""

    def send_single_email(self, *args, **kwargs) -> bool:
        """Template-Method: Versendet eine E-Mail

        Orchestriert den gesamten Email-Versand
        """
        from .exceptions import EmailSendError

        try:
            template_config = self.get_template_config(*args, **kwargs)
            html_content = template_config.render()
            payload = self.build_email_payload(
                *args, html_content=html_content, **kwargs
            )
            payload.validate()
            self._send_email(payload)

            logger.info(f"✓ Email versendet an {payload.recipient_email}")
            return True

        except Exception as e:
            logger.error(f"❌ Email Versand fehlgeschlagen: {e}")
            raise EmailSendError(f"Email Versand fehlgeschlagen: {e}")

    def send_bulk_emails(self, recipient_list: list) -> dict:
        """Versendet Emails an mehrere Empfänger"""
        result = {"sent": 0, "errors": 0, "failed": []}

        for recipient_data in recipient_list:
            try:
                self.send_single_email(**recipient_data)
                result["sent"] += 1
            except Exception as e:
                result["errors"] += 1
                result["failed"].append(
                    {"recipient": str(recipient_data), "error": str(e)}
                )
                logger.error(f"❌ Fehler bei {recipient_data}: {e}")

        return result

    def _send_email(self, payload: EmailPayload):
        """Interne Methode: Versendet Email via Django"""
        email = EmailMultiAlternatives(
            subject=payload.subject,
            body="Bitte verwende den HTML-Content",
            from_email=payload.from_email,
            to=[payload.recipient_email],
        )
        email.attach_alternative(payload.html_content, "text/html")
        email.send()
