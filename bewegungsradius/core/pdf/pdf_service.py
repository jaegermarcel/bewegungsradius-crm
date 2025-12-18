import os
import logging
from django.template.loader import render_to_string
from weasyprint import HTML
from django.conf import settings

logger = logging.getLogger(__name__)


# ==================== Exception Classes ====================

class PdfGenerationError(Exception):
    """Fehler bei PDF-Generierung"""
    pass


class FileStorageError(Exception):
    """Fehler beim Speichern von Dateien"""
    pass


# ==================== HTML to PDF Converter ====================

class HtmlToPdfConverter:
    """Konvertiert HTML-String zu PDF-Bytes (Generisch)"""

    def convert(self, html_string: str) -> bytes:
        """Konvertiert HTML zu PDF

        Args:
            html_string: HTML-String (beliebig)

        Returns:
            PDF als Bytes

        Raises:
            PdfGenerationError: Bei Fehler
        """
        try:
            html = HTML(string=html_string)
            pdf_bytes = html.write_pdf()

            if not pdf_bytes:
                raise PdfGenerationError("PDF-Generierung ergab leere Bytes")

            logger.info(f"PDF generated: {len(pdf_bytes)} bytes")
            return pdf_bytes
        except Exception as e:
            logger.error(f"HTML to PDF conversion failed: {e}", exc_info=True)
            raise PdfGenerationError(f"HTML zu PDF Konvertierung fehlgeschlagen: {e}")


# ==================== Template Rendering ====================

class TemplateRenderer:
    """Rendert beliebige Templates

    Generisch und nicht an ein spezifisches Model gebunden.
    """

    def render(self, template_name: str, context: dict) -> str:
        """Rendert Template mit Context

        Args:
            template_name: Template-Pfad (z.B. 'invoices/invoice_pdf.html')
            context: Template-Context als Dict

        Returns:
            Gerenderter HTML-String

        Raises:
            PdfGenerationError: Bei Rendering-Fehler
        """
        try:
            html = render_to_string(template_name, context)
            logger.info(f"Template {template_name} rendered: {len(html)} bytes")
            return html
        except Exception as e:
            logger.error(f"Template rendering failed for {template_name}: {e}", exc_info=True)
            raise PdfGenerationError(f"Template-Rendering fehlgeschlagen: {e}")


# ==================== File Storage ====================

class ConsumeFileStorage:
    """Speichert Dateien im consume-Verzeichnis (Paperless-Integration)

    Generisch und unabhängig vom Dateiinhalt.
    """

    def __init__(self, base_dir: str = None):
        """Initialisiert Storage mit optionalem Base Directory

        Args:
            base_dir: Custom base directory (default: settings.BASE_DIR)
        """
        self.base_dir = base_dir or settings.BASE_DIR

    def save(self, filename: str, content: bytes) -> str:
        """Speichert Datei im consume-Verzeichnis

        Args:
            filename: Dateiname (z.B. 'Rechnung_123.pdf')
            content: Dateiinhalt als Bytes

        Returns:
            Vollständiger Dateipfad

        Raises:
            FileStorageError: Bei Speicher-Fehler
        """
        try:
            directory = self._get_or_create_directory()
            filepath = os.path.join(directory, filename)

            with open(filepath, 'wb') as f:
                f.write(content)

            logger.info(f"File saved to consume: {filepath} ({len(content)} bytes)")
            return filepath
        except Exception as e:
            logger.error(f"Error saving to consume: {e}", exc_info=True)
            raise FileStorageError(f"Fehler beim Speichern in Consume: {e}")

    def exists(self, filename: str) -> bool:
        """Prüft ob Datei im consume-Verzeichnis existiert

        Args:
            filename: Dateiname

        Returns:
            True wenn existiert, False sonst
        """
        directory = self._get_directory()
        filepath = os.path.join(directory, filename)
        return os.path.exists(filepath)

    def _get_or_create_directory(self) -> str:
        """Erstellt consume-Verzeichnis if not exists"""
        directory = self._get_directory()
        os.makedirs(directory, exist_ok=True)
        return directory

    def _get_directory(self) -> str:
        """Gibt consume-Verzeichnispfad zurück"""
        return os.path.join(self.base_dir, 'consume')


# ==================== Core PDF Generation ====================

class PdfGenerator:
    """Generiert PDFs aus Templates

    ✅ Vollständig generisch
    ✅ Keine Invoice-Dependencies
    ✅ Kann für beliebige Models verwendet werden
    """

    def __init__(
            self,
            template_renderer: TemplateRenderer,
            converter: HtmlToPdfConverter,
    ):
        self.template_renderer = template_renderer
        self.converter = converter

    def generate(self, template_name: str, context: dict) -> bytes:
        """Generiert PDF aus Template

        Args:
            template_name: Template-Pfad
            context: Template-Context

        Returns:
            PDF als Bytes
        """
        html_string = self.template_renderer.render(template_name, context)
        pdf_bytes = self.converter.convert(html_string)
        return pdf_bytes


class PdfService:
    """High-Level PDF Service

    ✅ Generisch - kann für beliebige Dokumente verwendet werden
    ✅ Mit Storage Integration
    ✅ Logging und Error Handling
    """

    def __init__(
            self,
            pdf_generator: PdfGenerator,
            consume_storage: ConsumeFileStorage,
    ):
        self.pdf_generator = pdf_generator
        self.consume_storage = consume_storage

    def generate(self, template_name: str, context: dict) -> bytes:
        """Generiert PDF

        Args:
            template_name: Template-Pfad
            context: Template-Context

        Returns:
            PDF als Bytes
        """
        logger.info(f"Generating PDF from template {template_name}")
        pdf_bytes = self.pdf_generator.generate(template_name, context)
        logger.info(f"PDF generated: {len(pdf_bytes)} bytes")
        return pdf_bytes

    def generate_and_save(
            self,
            template_name: str,
            context: dict,
            filename: str
    ) -> bytes:
        """Generiert PDF und speichert im consume-Verzeichnis

        Args:
            template_name: Template-Pfad
            context: Template-Context
            filename: Dateiname

        Returns:
            PDF als Bytes
        """
        pdf_bytes = self.generate(template_name, context)

        try:
            self.consume_storage.save(filename, pdf_bytes)
        except FileStorageError as e:
            logger.error(f"Failed to save PDF to consume: {e}")
            # Trotzdem PDF zurückgeben

        return pdf_bytes


# ==================== Factory ====================

class PdfServiceFactory:
    """Factory für PdfService

    Erstellt vollständig konfigurierte PdfService-Instanzen.
    """

    @staticmethod
    def create(base_dir: str = None) -> PdfService:
        """Erstellt PdfService

        Args:
            base_dir: Custom base directory (default: settings.BASE_DIR)

        Returns:
            Vollständig konfigurierte PdfService-Instanz
        """
        template_renderer = TemplateRenderer()
        converter = HtmlToPdfConverter()

        pdf_generator = PdfGenerator(
            template_renderer=template_renderer,
            converter=converter,
        )

        consume_storage = ConsumeFileStorage(base_dir=base_dir)

        return PdfService(
            pdf_generator=pdf_generator,
            consume_storage=consume_storage,
        )