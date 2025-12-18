import logging
from bewegungsradius.core.pdf.pdf_service import (
    PdfService,
    PdfServiceFactory,
)

logger = logging.getLogger(__name__)


# ==================== Invoice-spezifischer Filename Generator ====================

class InvoiceFilenameGenerator:
    """Generiert Invoice-spezifische Dateinamen

    Basiert auf generischem System, aber mit Invoice-Context.
    """

    @staticmethod
    def generate_invoice_filename(invoice_number: str) -> str:
        """Generiert Invoice-Dateiname

        Args:
            invoice_number: Invoice-Nummer (z.B. 'INV-2025-001')

        Returns:
            Dateiname (z.B. 'Rechnung_INV-2025-001.pdf')
        """
        return f"Rechnung_{invoice_number}.pdf"

    @staticmethod
    def generate_cancellation_filename(invoice_number: str) -> str:
        """Generiert Storno-Dateiname

        Args:
            invoice_number: Invoice-Nummer

        Returns:
            Dateiname (z.B. 'Storno_INV-2025-001.pdf')
        """
        return f"Storno_{invoice_number}.pdf"


# ==================== Invoice PDF Service ====================

class InvoicePdfService:
    """High-Level Invoice PDF Service

    ✅ Nutzt generische PdfService
    ✅ Invoice-spezifische Methoden
    ✅ Zentrale Schnittstelle für Invoice PDFs
    """

    def __init__(self, pdf_service: PdfService = None):
        """Initialisiert mit generischem PdfService

        Args:
            pdf_service: Custom PdfService (default: neu erstellt)
        """
        self.pdf_service = pdf_service or PdfServiceFactory.create()

    def generate_invoice(self, invoice) -> bytes:
        """Generiert Invoice-PDF

        Args:
            invoice: Invoice-Model

        Returns:
            PDF als Bytes
        """
        logger.info(f"Generating invoice PDF for {invoice.invoice_number}")

        context = self._build_invoice_context(invoice)
        pdf_bytes = self.pdf_service.generate(
            template_name='invoices/invoice_pdf.html',
            context=context
        )

        logger.info(f"Invoice PDF generated: {len(pdf_bytes)} bytes")
        return pdf_bytes

    def generate_cancellation(self, invoice) -> bytes:
        """Generiert Storno-PDF

        Args:
            invoice: Invoice-Model (must be cancelled)

        Returns:
            PDF als Bytes
        """
        logger.info(f"Generating cancellation PDF for {invoice.invoice_number}")

        context = self._build_invoice_context(invoice)
        pdf_bytes = self.pdf_service.generate(
            template_name='invoices/cancellation_pdf.html',
            context=context
        )

        logger.info(f"Cancellation PDF generated: {len(pdf_bytes)} bytes")
        return pdf_bytes

    def generate_and_save_invoice(self, invoice) -> bytes:
        """Generiert Invoice-PDF und speichert im consume/

        Args:
            invoice: Invoice-Model

        Returns:
            PDF als Bytes
        """
        filename = InvoiceFilenameGenerator.generate_invoice_filename(
            invoice.invoice_number
        )
        context = self._build_invoice_context(invoice)

        pdf_bytes = self.pdf_service.generate_and_save(
            template_name='invoices/invoice_pdf.html',
            context=context,
            filename=filename
        )

        return pdf_bytes

    def generate_and_save_cancellation(self, invoice) -> bytes:
        """Generiert Storno-PDF und speichert im consume/

        Args:
            invoice: Invoice-Model (must be cancelled)

        Returns:
            PDF als Bytes
        """
        filename = InvoiceFilenameGenerator.generate_cancellation_filename(
            invoice.invoice_number
        )
        context = self._build_invoice_context(invoice)

        pdf_bytes = self.pdf_service.generate_and_save(
            template_name='invoices/cancellation_pdf.html',
            context=context,
            filename=filename
        )

        return pdf_bytes

    def _build_invoice_context(self, invoice) -> dict:
        """Baut Template-Context für Invoice

        Args:
            invoice: Invoice-Model

        Returns:
            Context-Dict für Template
        """
        from company.models import CompanyInfo

        company = CompanyInfo.objects.filter().first()

        return {
            'invoice': invoice,
            'company': company,
        }


# ==================== Factory ====================

class InvoicePdfServiceFactory:
    """Factory für InvoicePdfService"""

    @staticmethod
    def create() -> InvoicePdfService:
        """Erstellt InvoicePdfService

        Returns:
            Vollständig konfigurierte InvoicePdfService-Instanz
        """
        pdf_service = PdfServiceFactory.create()
        return InvoicePdfService(pdf_service=pdf_service)


# ==================== Legacy Compatibility ====================

def generate_invoice_pdf(invoice) -> bytes:
    """Legacy-Funktion für Rückwärtskompatibilität

    Achtung: Diese Funktion wird in Zukunft deprecated.
    Nutze stattdessen: InvoicePdfServiceFactory.create().generate_and_save_invoice()
    """
    service = InvoicePdfServiceFactory.create()
    return service.generate_and_save_invoice(invoice)


def generate_cancellation_pdf(invoice) -> bytes:
    """Legacy-Funktion für Rückwärtskompatibilität

    Achtung: Diese Funktion wird in Zukunft deprecated.
    Nutze stattdessen: InvoicePdfServiceFactory.create().generate_and_save_cancellation()
    """
    service = InvoicePdfServiceFactory.create()
    return service.generate_and_save_cancellation(invoice)