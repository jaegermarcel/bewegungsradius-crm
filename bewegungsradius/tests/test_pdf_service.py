"""
core/tests/test_pdf_service.py - Tests für Core PDF Service
============================================================
✅ HtmlToPdfConverter
✅ TemplateRenderer
✅ ConsumeFileStorage
✅ PdfGenerator
✅ PdfService
✅ PdfServiceFactory
✅ Exception Classes
"""

import pytest
import os
import tempfile
from unittest.mock import MagicMock, patch
from django.template.exceptions import TemplateDoesNotExist

pytestmark = pytest.mark.django_db

# ==================== IMPORTS ====================

from bewegungsradius.core.pdf.pdf_service import (
    HtmlToPdfConverter,
    TemplateRenderer,
    ConsumeFileStorage,
    PdfGenerator,
    PdfService,
    PdfServiceFactory,
    PdfGenerationError,
    FileStorageError,
)


# ==================== FIXTURES ====================

@pytest.fixture
def html_string():
    """Sample HTML string"""
    return '<html><body><h1>Test Document</h1></body></html>'


@pytest.fixture
def pdf_bytes():
    """Sample PDF bytes"""
    return b'%PDF-1.4\n%fake pdf content'


@pytest.fixture
def temp_dir():
    """Temporary directory for file storage tests"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


# ==================== EXCEPTION TESTS ====================

class TestExceptions:
    """Tests für Custom Exceptions"""

    def test_pdf_generation_error_is_exception(self):
        """Test: PdfGenerationError ist Exception"""
        error = PdfGenerationError("Test error")
        assert isinstance(error, Exception)
        assert str(error) == "Test error"

    def test_file_storage_error_is_exception(self):
        """Test: FileStorageError ist Exception"""
        error = FileStorageError("Storage failed")
        assert isinstance(error, Exception)
        assert str(error) == "Storage failed"


# ==================== HTML TO PDF CONVERTER TESTS ====================

class TestHtmlToPdfConverter:
    """Tests für HtmlToPdfConverter"""

    def test_converter_initialization(self):
        """Test: Converter wird erstellt"""
        converter = HtmlToPdfConverter()
        assert converter is not None

    @patch('bewegungsradius.core.pdf.pdf_service.HTML')
    def test_convert_returns_pdf_bytes(self, mock_html, html_string, pdf_bytes):
        """Test: convert() gibt PDF-Bytes zurück"""
        mock_html_instance = MagicMock()
        mock_html_instance.write_pdf.return_value = pdf_bytes
        mock_html.return_value = mock_html_instance

        converter = HtmlToPdfConverter()
        result = converter.convert(html_string)

        assert result == pdf_bytes
        assert isinstance(result, bytes)
        mock_html.assert_called_once_with(string=html_string)

    @patch('bewegungsradius.core.pdf.pdf_service.HTML')
    def test_convert_logs_success(self, mock_html, html_string, pdf_bytes):
        """Test: Logging bei erfolgreicher Konvertierung"""
        mock_html_instance = MagicMock()
        mock_html_instance.write_pdf.return_value = pdf_bytes
        mock_html.return_value = mock_html_instance

        with patch('bewegungsradius.core.pdf.pdf_service.logger') as mock_logger:
            converter = HtmlToPdfConverter()
            converter.convert(html_string)

            mock_logger.info.assert_called()
            call_args = str(mock_logger.info.call_args)
            assert 'bytes' in call_args

    @patch('bewegungsradius.core.pdf.pdf_service.HTML')
    def test_convert_empty_pdf_raises_error(self, mock_html, html_string):
        """Test: Error bei leeren PDF-Bytes"""
        mock_html_instance = MagicMock()
        mock_html_instance.write_pdf.return_value = b''
        mock_html.return_value = mock_html_instance

        converter = HtmlToPdfConverter()

        with pytest.raises(PdfGenerationError) as exc_info:
            converter.convert(html_string)

        assert 'leere Bytes' in str(exc_info.value)

    @patch('bewegungsradius.core.pdf.pdf_service.HTML')
    def test_convert_none_pdf_raises_error(self, mock_html, html_string):
        """Test: Error bei None als PDF"""
        mock_html_instance = MagicMock()
        mock_html_instance.write_pdf.return_value = None
        mock_html.return_value = mock_html_instance

        converter = HtmlToPdfConverter()

        with pytest.raises(PdfGenerationError):
            converter.convert(html_string)

    @patch('bewegungsradius.core.pdf.pdf_service.HTML')
    def test_convert_exception_handling(self, mock_html, html_string):
        """Test: Exception Handling bei PDF-Fehler"""
        mock_html.side_effect = Exception("WeasyPrint Error")

        converter = HtmlToPdfConverter()

        with pytest.raises(PdfGenerationError) as exc_info:
            converter.convert(html_string)

        assert 'WeasyPrint Error' in str(exc_info.value)

    @patch('bewegungsradius.core.pdf.pdf_service.HTML')
    def test_convert_logs_error(self, mock_html, html_string):
        """Test: Error wird geloggt"""
        mock_html.side_effect = Exception("Test Error")

        with patch('bewegungsradius.core.pdf.pdf_service.logger') as mock_logger:
            converter = HtmlToPdfConverter()

            with pytest.raises(PdfGenerationError):
                converter.convert(html_string)

            mock_logger.error.assert_called()


# ==================== TEMPLATE RENDERER TESTS ====================

class TestTemplateRenderer:
    """Tests für TemplateRenderer"""

    def test_renderer_initialization(self):
        """Test: Renderer wird erstellt"""
        renderer = TemplateRenderer()
        assert renderer is not None

    @patch('bewegungsradius.core.pdf.pdf_service.render_to_string')
    def test_render_returns_html(self, mock_render):
        """Test: render() gibt HTML zurück"""
        html_content = '<html>Test</html>'
        mock_render.return_value = html_content

        renderer = TemplateRenderer()
        context = {'title': 'Test'}
        result = renderer.render('test.html', context)

        assert result == html_content
        mock_render.assert_called_once_with('test.html', context)

    @patch('bewegungsradius.core.pdf.pdf_service.render_to_string')
    def test_render_logs_success(self, mock_render):
        """Test: Logging bei erfolgreichem Rendering"""
        mock_render.return_value = '<html>Test</html>'

        with patch('bewegungsradius.core.pdf.pdf_service.logger') as mock_logger:
            renderer = TemplateRenderer()
            renderer.render('test.html', {})

            mock_logger.info.assert_called()
            call_args = str(mock_logger.info.call_args)
            assert 'rendered' in call_args

    @patch('bewegungsradius.core.pdf.pdf_service.render_to_string')
    def test_render_template_not_found(self, mock_render):
        """Test: Exception bei nicht gefundenem Template"""
        mock_render.side_effect = TemplateDoesNotExist("Template not found")

        renderer = TemplateRenderer()

        with pytest.raises(PdfGenerationError) as exc_info:
            renderer.render('nonexistent.html', {})

        assert 'Template-Rendering fehlgeschlagen' in str(exc_info.value)

    @patch('bewegungsradius.core.pdf.pdf_service.render_to_string')
    def test_render_logs_error(self, mock_render):
        """Test: Error wird geloggt"""
        mock_render.side_effect = Exception("Rendering Error")

        with patch('bewegungsradius.core.pdf.pdf_service.logger') as mock_logger:
            renderer = TemplateRenderer()

            with pytest.raises(PdfGenerationError):
                renderer.render('test.html', {})

            mock_logger.error.assert_called()

    @patch('bewegungsradius.core.pdf.pdf_service.render_to_string')
    def test_render_with_complex_context(self, mock_render):
        """Test: Rendering mit komplexem Context"""
        mock_render.return_value = '<html>Complex</html>'

        renderer = TemplateRenderer()
        context = {
            'title': 'Test',
            'items': [1, 2, 3],
            'nested': {'key': 'value'}
        }
        result = renderer.render('test.html', context)

        assert result == '<html>Complex</html>'
        mock_render.assert_called_once_with('test.html', context)


# ==================== CONSUME FILE STORAGE TESTS ====================

class TestConsumeFileStorage:
    """Tests für ConsumeFileStorage"""

    def test_storage_initialization_default(self):
        """Test: Storage mit default base_dir"""
        storage = ConsumeFileStorage()
        assert storage is not None
        assert storage.base_dir is not None

    def test_storage_initialization_custom_base_dir(self):
        """Test: Storage mit custom base_dir"""
        custom_dir = '/custom/path'
        storage = ConsumeFileStorage(base_dir=custom_dir)
        assert storage.base_dir == custom_dir

    def test_get_directory(self, temp_dir):
        """Test: Consume-Verzeichnis wird richtig bestimmt"""
        storage = ConsumeFileStorage(base_dir=temp_dir)
        directory = storage._get_directory()

        assert 'consume' in directory
        assert temp_dir in directory

    def test_save_creates_directory(self, temp_dir):
        """Test: Verzeichnis wird erstellt wenn nicht existent"""
        storage = ConsumeFileStorage(base_dir=temp_dir)
        content = b'test pdf content'

        filepath = storage.save('test.pdf', content)

        assert os.path.exists(filepath)
        assert os.path.isfile(filepath)

    def test_save_writes_content(self, temp_dir):
        """Test: Datei wird mit korrektem Inhalt geschrieben"""
        storage = ConsumeFileStorage(base_dir=temp_dir)
        content = b'test pdf content'

        filepath = storage.save('test.pdf', content)

        with open(filepath, 'rb') as f:
            saved_content = f.read()

        assert saved_content == content

    def test_save_returns_filepath(self, temp_dir):
        """Test: save() gibt korrekten Pfad zurück"""
        storage = ConsumeFileStorage(base_dir=temp_dir)
        content = b'test pdf content'

        filepath = storage.save('test.pdf', content)

        assert 'test.pdf' in filepath
        assert isinstance(filepath, str)
        assert filepath.endswith('test.pdf')

    def test_save_logs_success(self, temp_dir):
        """Test: Logging bei erfolgreichem Speichern"""
        with patch('bewegungsradius.core.pdf.pdf_service.logger') as mock_logger:
            storage = ConsumeFileStorage(base_dir=temp_dir)
            content = b'test pdf content'
            storage.save('test.pdf', content)

            mock_logger.info.assert_called()
            call_args = str(mock_logger.info.call_args)
            assert 'saved' in call_args.lower()

    def test_exists_true(self, temp_dir):
        """Test: exists() gibt True zurück wenn Datei existiert"""
        storage = ConsumeFileStorage(base_dir=temp_dir)
        content = b'test pdf content'

        # Erst speichern
        storage.save('test.pdf', content)

        # Dann prüfen
        exists = storage.exists('test.pdf')
        assert exists is True

    def test_exists_false(self, temp_dir):
        """Test: exists() gibt False zurück wenn Datei nicht existiert"""
        storage = ConsumeFileStorage(base_dir=temp_dir)

        exists = storage.exists('nonexistent.pdf')
        assert exists is False

    def test_save_multiple_files(self, temp_dir):
        """Test: Mehrere Dateien speichern"""
        storage = ConsumeFileStorage(base_dir=temp_dir)

        filepath1 = storage.save('file1.pdf', b'content1')
        filepath2 = storage.save('file2.pdf', b'content2')

        assert os.path.exists(filepath1)
        assert os.path.exists(filepath2)
        assert filepath1 != filepath2


# ==================== PDF GENERATOR TESTS ====================

class TestPdfGenerator:
    """Tests für PdfGenerator"""

    def test_generator_initialization(self):
        """Test: Generator wird erstellt"""
        mock_renderer = MagicMock()
        mock_converter = MagicMock()

        generator = PdfGenerator(
            template_renderer=mock_renderer,
            converter=mock_converter
        )

        assert generator is not None
        assert generator.template_renderer == mock_renderer
        assert generator.converter == mock_converter

    def test_generate_calls_renderer_and_converter(self):
        """Test: generate() ruft Renderer und Converter auf"""
        mock_renderer = MagicMock()
        mock_renderer.render.return_value = '<html>Test</html>'

        mock_converter = MagicMock()
        mock_converter.convert.return_value = b'pdf_bytes'

        generator = PdfGenerator(
            template_renderer=mock_renderer,
            converter=mock_converter
        )

        context = {'title': 'Test'}
        result = generator.generate('test.html', context)

        assert result == b'pdf_bytes'
        mock_renderer.render.assert_called_once_with('test.html', context)
        mock_converter.convert.assert_called_once_with('<html>Test</html>')

    def test_generate_returns_bytes(self):
        """Test: generate() gibt Bytes zurück"""
        mock_renderer = MagicMock()
        mock_renderer.render.return_value = '<html>Test</html>'

        mock_converter = MagicMock()
        mock_converter.convert.return_value = b'pdf_bytes'

        generator = PdfGenerator(
            template_renderer=mock_renderer,
            converter=mock_converter
        )

        result = generator.generate('test.html', {})

        assert isinstance(result, bytes)


# ==================== PDF SERVICE TESTS ====================

class TestPdfService:
    """Tests für PdfService"""

    def test_service_initialization(self):
        """Test: Service wird erstellt"""
        mock_generator = MagicMock()
        mock_storage = MagicMock()

        service = PdfService(
            pdf_generator=mock_generator,
            consume_storage=mock_storage
        )

        assert service is not None
        assert service.pdf_generator == mock_generator
        assert service.consume_storage == mock_storage

    def test_generate_calls_generator(self):
        """Test: generate() ruft Generator auf"""
        mock_generator = MagicMock()
        mock_generator.generate.return_value = b'pdf_bytes'

        mock_storage = MagicMock()

        service = PdfService(
            pdf_generator=mock_generator,
            consume_storage=mock_storage
        )

        context = {'title': 'Test'}
        result = service.generate('test.html', context)

        assert result == b'pdf_bytes'
        mock_generator.generate.assert_called_once_with('test.html', context)

    def test_generate_logs_info(self):
        """Test: generate() loggt Info"""
        mock_generator = MagicMock()
        mock_generator.generate.return_value = b'pdf_bytes'

        mock_storage = MagicMock()

        with patch('bewegungsradius.core.pdf.pdf_service.logger') as mock_logger:
            service = PdfService(
                pdf_generator=mock_generator,
                consume_storage=mock_storage
            )

            service.generate('test.html', {})

            assert mock_logger.info.call_count >= 2  # Start + End

    def test_generate_and_save_saves_file(self):
        """Test: generate_and_save() speichert Datei"""
        mock_generator = MagicMock()
        mock_generator.generate.return_value = b'pdf_bytes'

        mock_storage = MagicMock()
        mock_storage.save.return_value = '/path/to/file.pdf'

        service = PdfService(
            pdf_generator=mock_generator,
            consume_storage=mock_storage
        )

        result = service.generate_and_save('test.html', {}, 'output.pdf')

        assert result == b'pdf_bytes'
        mock_storage.save.assert_called_once_with('output.pdf', b'pdf_bytes')

    def test_generate_and_save_handles_storage_error(self):
        """Test: generate_and_save() handled Storage-Error"""
        mock_generator = MagicMock()
        mock_generator.generate.return_value = b'pdf_bytes'

        mock_storage = MagicMock()
        mock_storage.save.side_effect = FileStorageError("Storage failed")

        service = PdfService(
            pdf_generator=mock_generator,
            consume_storage=mock_storage
        )

        # Sollte PDF trotzdem zurückgeben
        result = service.generate_and_save('test.html', {}, 'output.pdf')

        assert result == b'pdf_bytes'

    def test_generate_and_save_logs_storage_error(self):
        """Test: Storage-Error wird geloggt"""
        mock_generator = MagicMock()
        mock_generator.generate.return_value = b'pdf_bytes'

        mock_storage = MagicMock()
        mock_storage.save.side_effect = FileStorageError("Storage failed")

        with patch('bewegungsradius.core.pdf.pdf_service.logger') as mock_logger:
            service = PdfService(
                pdf_generator=mock_generator,
                consume_storage=mock_storage
            )

            service.generate_and_save('test.html', {}, 'output.pdf')

            mock_logger.error.assert_called()


# ==================== PDF SERVICE FACTORY TESTS ====================

class TestPdfServiceFactory:
    """Tests für PdfServiceFactory"""

    def test_factory_creates_service(self):
        """Test: Factory erstellt PdfService"""
        service = PdfServiceFactory.create()

        assert service is not None
        assert isinstance(service, PdfService)

    def test_factory_creates_with_all_dependencies(self):
        """Test: Factory erstellt Service mit allen Dependencies"""
        service = PdfServiceFactory.create()

        assert hasattr(service, 'pdf_generator')
        assert hasattr(service, 'consume_storage')
        assert isinstance(service.pdf_generator, PdfGenerator)
        assert isinstance(service.consume_storage, ConsumeFileStorage)

    def test_factory_creates_complete_pdf_generator(self):
        """Test: Factory erstellt kompletten PdfGenerator"""
        service = PdfServiceFactory.create()

        assert hasattr(service.pdf_generator, 'template_renderer')
        assert hasattr(service.pdf_generator, 'converter')
        assert isinstance(service.pdf_generator.template_renderer, TemplateRenderer)
        assert isinstance(service.pdf_generator.converter, HtmlToPdfConverter)

    def test_factory_with_custom_base_dir(self):
        """Test: Factory mit custom base_dir"""
        custom_dir = '/custom/path'
        service = PdfServiceFactory.create(base_dir=custom_dir)

        assert service.consume_storage.base_dir == custom_dir


# ==================== INTEGRATION TESTS ====================

class TestPdfServiceIntegration:
    """Integration Tests"""

    @patch('bewegungsradius.core.pdf.pdf_service.render_to_string')
    @patch('bewegungsradius.core.pdf.pdf_service.HTML')
    def test_full_pdf_generation_flow(self, mock_html, mock_render, pdf_bytes, temp_dir):
        """Test: Kompletter PDF-Generierungsprozess"""
        # Setup mocks
        mock_render.return_value = '<html>Test</html>'
        mock_html_instance = MagicMock()
        mock_html_instance.write_pdf.return_value = pdf_bytes
        mock_html.return_value = mock_html_instance

        # Create service
        service = PdfServiceFactory.create(base_dir=temp_dir)

        # Generate PDF
        context = {'title': 'Test'}
        result = service.generate('test.html', context)

        # Verify
        assert result == pdf_bytes
        assert len(result) > 0

    @patch('bewegungsradius.core.pdf.pdf_service.render_to_string')
    @patch('bewegungsradius.core.pdf.pdf_service.HTML')
    def test_full_pdf_generation_and_save_flow(self, mock_html, mock_render, pdf_bytes, temp_dir):
        """Test: PDF Generierung + Speicherung"""
        # Setup mocks
        mock_render.return_value = '<html>Test</html>'
        mock_html_instance = MagicMock()
        mock_html_instance.write_pdf.return_value = pdf_bytes
        mock_html.return_value = mock_html_instance

        # Create service
        service = PdfServiceFactory.create(base_dir=temp_dir)

        # Generate and save PDF
        result = service.generate_and_save('test.html', {}, 'output.pdf')

        # Verify
        assert result == pdf_bytes

        # Check file exists
        consume_dir = os.path.join(temp_dir, 'consume')
        filepath = os.path.join(consume_dir, 'output.pdf')
        assert os.path.exists(filepath)