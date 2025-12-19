import logging

from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags

from bewegungsradius.core.email import (
    BaseEmailService,
    EmailPayload,
    EmailTemplateConfig,
)

logger = logging.getLogger(__name__)


class InvoiceEmailService(BaseEmailService):
    """Service für Invoice Email Versand mit PDF-Attachment"""

    TEMPLATE_PATH = "email/notifications/invoice_email.html"

    def get_template_config(self, invoice, **kwargs) -> EmailTemplateConfig:
        """Erstellt Template Config für Invoice Email"""
        customer = invoice.customer

        context = {
            "customer": customer,
            "invoice": invoice,
            "company": self.company_info,
        }
        return EmailTemplateConfig(self.TEMPLATE_PATH, context)

    def build_email_payload(
        self, invoice, html_content: str = None, **kwargs
    ) -> EmailPayload:
        """Erstellt Email Payload für Invoice"""
        customer = invoice.customer
        subject = f"Rechnung {invoice.invoice_number}"

        return EmailPayload(
            subject=subject,
            html_content=html_content or "",
            recipient_email=customer.email,
            from_email=self.company_info.email if self.company_info else None,
        )

    def send_invoice_email(self, invoice) -> dict:
        """
        Versendet Invoice Email mit PDF-Attachment

        ✅ Nutzt BaseEmailService.send_single_email() + PDF
        ✅ Lädt PDF vor Versand
        ✅ Hängt PDF an Email an
        """
        from invoices.pdf_service import generate_invoice_pdf

        customer = invoice.customer

        if not customer.email:
            logger.warning(f"Kunde {customer.id} hat keine Email-Adresse")
            return {
                "sent": 0,
                "errors": 1,
                "failed": [
                    {
                        "recipient": customer.get_full_name(),
                        "error": "Kunde hat keine Email-Adresse",
                    }
                ],
            }

        try:
            # Template Config generieren
            template_config = self.get_template_config(invoice)

            # Template rendern
            html_content = template_config.render()

            # Email Payload generieren
            payload = self.build_email_payload(invoice, html_content=html_content)

            # Validiere Payload
            payload.validate()

            # PDF generieren
            try:
                pdf_bytes = generate_invoice_pdf(invoice)
                logger.info(f"✓ PDF generiert für Rechnung {invoice.invoice_number}")
            except Exception as e:
                logger.error(f"❌ PDF Generierung fehlgeschlagen: {e}")
                pdf_bytes = None

            # Email mit Attachment versenden
            self._send_email_with_attachment(payload, pdf_bytes, invoice.invoice_number)

            logger.info(
                f"✓ Invoice Email an {customer.email} versendet: {payload.subject}"
            )

            return {"sent": 1, "errors": 0, "invoice_number": invoice.invoice_number}

        except Exception as e:
            logger.error(f"❌ Email Versand fehlgeschlagen: {e}", exc_info=True)

            return {
                "sent": 0,
                "errors": 1,
                "failed": [{"recipient": customer.get_full_name(), "error": str(e)}],
            }

    def _send_email_with_attachment(
        self, payload: EmailPayload, pdf_bytes: bytes = None, invoice_number: str = None
    ):
        """
        Versendet Email mit optionalem PDF-Attachment

        Args:
            payload: EmailPayload Objekt
            pdf_bytes: PDF Bytes (optional)
            invoice_number: Rechnungsnummer für Dateiname
        """
        try:
            plain_message = strip_tags(payload.html_content)

            email = EmailMultiAlternatives(
                subject=payload.subject,
                body=plain_message,
                from_email=payload.from_email,
                to=[payload.recipient_email],
            )

            # HTML-Version anhängen
            email.attach_alternative(payload.html_content, "text/html")

            # PDF anhängen wenn vorhanden
            if pdf_bytes and invoice_number:
                filename = f"Rechnung_{invoice_number}.pdf"
                email.attach(filename, pdf_bytes, "application/pdf")
                logger.info(f"✓ PDF {filename} als Attachment hinzugefügt")

            # Versenden
            email.send(fail_silently=False)
            logger.info(
                f"✓ Email mit Attachment versendet an {payload.recipient_email}"
            )

        except Exception as e:
            logger.error(f"❌ Email mit Attachment fehlgeschlagen: {e}", exc_info=True)
            raise

    def send_bulk_invoice_emails(self, invoices) -> dict:
        """
        Versendet Emails für mehrere Rechnungen

        Args:
            invoices: QuerySet oder List von Invoice Objekten

        Returns:
            dict mit sent, errors, failed
        """
        result = {"sent": 0, "errors": 0, "failed": []}

        for invoice in invoices:
            try:
                invoice_result = self.send_invoice_email(invoice)
                result["sent"] += invoice_result.get("sent", 0)
                result["errors"] += invoice_result.get("errors", 0)

                if invoice_result.get("failed"):
                    result["failed"].extend(invoice_result["failed"])

            except Exception as e:
                logger.error(
                    f"❌ Fehler beim Versand für Rechnung {invoice.invoice_number}: {e}"
                )
                result["errors"] += 1
                result["failed"].append(
                    {"invoice": invoice.invoice_number, "error": str(e)}
                )

        return result
