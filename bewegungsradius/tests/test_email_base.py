"""
tests/test_email_base.py - Tests für BaseEmailService (pytest)
==============================================================
✅ Unit Tests für Email-Services
✅ Alle Dependencies gemodelt
✅ Keine echten Templates nötig
"""

from unittest.mock import Mock, patch

import pytest

pytestmark = pytest.mark.django_db

from bewegungsradius.core.email import (BaseEmailService, EmailPayload,
                                        EmailTemplateConfig)
from bewegungsradius.core.email.exceptions import (EmailSendError,
                                                   EmailValidationError)

# ==================== TEST DOUBLES ====================


class ConcreteEmailService(BaseEmailService):
    """Konkrete Implementierung von BaseEmailService für Tests"""

    def get_template_config(self, **kwargs) -> EmailTemplateConfig:
        """Implementierung für Tests"""
        return EmailTemplateConfig(
            "test_template.html", {"customer": kwargs.get("customer")}
        )

    def build_email_payload(self, html_content: str = None, **kwargs) -> EmailPayload:
        """Implementierung für Tests"""
        return EmailPayload(
            subject="Test Subject",
            html_content=html_content or "<p>Test</p>",
            recipient_email=kwargs.get("email", "test@example.com"),
            from_email="sender@example.com",
        )


# ==================== EMAIL PAYLOAD TESTS ====================


class TestEmailPayload:
    """Tests für EmailPayload Value Object"""

    def test_payload_initialization(self):
        """Payload wird mit allen Feldern initialisiert"""
        payload = EmailPayload(
            subject="Test",
            html_content="<p>Content</p>",
            recipient_email="test@example.com",
            from_email="sender@example.com",
        )

        assert payload.subject == "Test"
        assert payload.html_content == "<p>Content</p>"
        assert payload.recipient_email == "test@example.com"
        assert payload.from_email == "sender@example.com"

    @patch("django.conf.settings.DEFAULT_FROM_EMAIL", "default@example.com")
    def test_payload_uses_default_from_email(self):
        """Wenn from_email nicht gesetzt, nutze DEFAULT_FROM_EMAIL"""
        payload = EmailPayload(
            subject="Test",
            html_content="<p>Content</p>",
            recipient_email="test@example.com",
        )
        assert payload.from_email == "default@example.com"

    def test_validate_requires_subject(self):
        """Validierung schlägt fehl ohne Subject"""
        payload = EmailPayload(
            subject="",
            html_content="<p>Content</p>",
            recipient_email="test@example.com",
        )

        with pytest.raises(EmailValidationError):
            payload.validate()

    def test_validate_requires_html_content(self):
        """Validierung schlägt fehl ohne HTML-Content"""
        payload = EmailPayload(
            subject="Test", html_content="", recipient_email="test@example.com"
        )

        with pytest.raises(EmailValidationError):
            payload.validate()

    def test_validate_requires_recipient_email(self):
        """Validierung schlägt fehl ohne Recipient Email"""
        payload = EmailPayload(
            subject="Test", html_content="<p>Content</p>", recipient_email=""
        )

        with pytest.raises(EmailValidationError):
            payload.validate()

    def test_validate_succeeds_with_all_fields(self):
        """Validierung erfolgreich mit allen Feldern"""
        payload = EmailPayload(
            subject="Test",
            html_content="<p>Content</p>",
            recipient_email="test@example.com",
        )

        # Sollte keine Exception werfen
        payload.validate()


# ==================== EMAIL TEMPLATE CONFIG TESTS ====================


class TestEmailTemplateConfig:
    """Tests für EmailTemplateConfig Value Object"""

    def test_template_config_initialization(self):
        """TemplateConfig wird mit Pfad und Context initialisiert"""
        config = EmailTemplateConfig(
            "email/test.html", {"customer": "John", "course": "Yoga"}
        )

        assert config.template_path == "email/test.html"
        assert config.context["customer"] == "John"

    @patch("bewegungsradius.core.email.base.render_to_string")
    def test_render_returns_html(self, mock_render):
        """render() gibt HTML String zurück"""
        mock_render.return_value = "<p>Rendered HTML</p>"

        config = EmailTemplateConfig("email/test.html", {"customer": "John"})
        result = config.render()

        assert result == "<p>Rendered HTML</p>"
        mock_render.assert_called_once()


# ==================== BASE EMAIL SERVICE TESTS ====================


class TestBaseEmailService:
    """Tests für BaseEmailService"""

    @pytest.fixture
    def service(self):
        """Service Fixture"""
        service = ConcreteEmailService()
        service.company_info = Mock(name="CompanyInfo")
        return service

    def test_service_initialization(self):
        """Service wird mit company_info initialisiert"""
        company = Mock()
        service = ConcreteEmailService(company)

        assert service.company_info == company

    # ==================== send_single_email Tests ====================

    @patch("bewegungsradius.core.email.base.render_to_string")
    @patch.object(BaseEmailService, "_send_email")
    def test_send_single_email_success(self, mock_send, mock_render, service):
        """send_single_email versendet Email erfolgreich"""
        mock_render.return_value = "<p>Test</p>"

        result = service.send_single_email(email="test@example.com")

        assert result is True
        mock_send.assert_called_once()

    @patch("bewegungsradius.core.email.base.render_to_string")
    def test_send_single_email_raises_on_validation_error(self, mock_render, service):
        """send_single_email wirft EmailSendError bei Validierungsfehler"""
        mock_render.return_value = "<p>Test</p>"

        def mock_build(*args, **kwargs):
            return EmailPayload(
                subject="Test",
                html_content="<p>Test</p>",
                recipient_email="",  # Leere Email → Fehler!
            )

        with patch.object(service, "build_email_payload", mock_build):
            with pytest.raises(EmailSendError):
                service.send_single_email()

    @patch("bewegungsradius.core.email.base.render_to_string")
    @patch.object(BaseEmailService, "_send_email")
    def test_send_single_email_logs_success(
        self, mock_send, mock_render, service, caplog
    ):
        """send_single_email loggt erfolgreichen Versand"""
        import logging

        caplog.set_level(logging.INFO)
        mock_render.return_value = "<p>Test</p>"

        service.send_single_email(email="test@example.com")

        # Check dass 'Email versendet' im Log ist
        log_messages = [record.message for record in caplog.records]
        assert any("Email versendet" in msg for msg in log_messages)

    # ==================== send_bulk_emails Tests ====================

    @patch.object(BaseEmailService, "send_single_email")
    def test_send_bulk_emails_success(self, mock_send, service):
        """send_bulk_emails versendet mehrere Emails"""
        mock_send.return_value = True

        recipients = [
            {"email": "user1@example.com"},
            {"email": "user2@example.com"},
            {"email": "user3@example.com"},
        ]

        result = service.send_bulk_emails(recipients)

        assert result["sent"] == 3
        assert result["errors"] == 0
        assert len(result["failed"]) == 0
        assert mock_send.call_count == 3

    @patch.object(BaseEmailService, "send_single_email")
    def test_send_bulk_emails_handles_errors(self, mock_send, service):
        """send_bulk_emails behandelt Fehler korrekt"""
        mock_send.side_effect = [True, EmailSendError("Send failed"), True]

        recipients = [
            {"email": "user1@example.com"},
            {"email": "user2@example.com"},
            {"email": "user3@example.com"},
        ]

        result = service.send_bulk_emails(recipients)

        assert result["sent"] == 2
        assert result["errors"] == 1
        assert len(result["failed"]) == 1

    @patch.object(BaseEmailService, "send_single_email")
    def test_send_bulk_emails_empty_list(self, mock_send, service):
        """send_bulk_emails mit leerer Liste"""
        result = service.send_bulk_emails([])

        assert result["sent"] == 0
        assert result["errors"] == 0
        mock_send.assert_not_called()

    @patch.object(BaseEmailService, "send_single_email")
    def test_send_bulk_emails_continues_on_error(self, mock_send, service):
        """send_bulk_emails setzt fort, auch wenn eine Email fehlschlägt"""
        mock_send.side_effect = EmailSendError("Error")

        recipients = [
            {"email": "user1@example.com"},
            {"email": "user2@example.com"},
        ]

        result = service.send_bulk_emails(recipients)

        assert result["errors"] == 2
        assert mock_send.call_count == 2

    # ==================== _send_email Tests ====================

    @patch("bewegungsradius.core.email.base.EmailMultiAlternatives")
    def test_send_email_creates_email(self, mock_email_class, service):
        """_send_email erstellt EmailMultiAlternatives Objekt"""
        mock_email_instance = Mock()
        mock_email_class.return_value = mock_email_instance

        payload = EmailPayload(
            subject="Test",
            html_content="<p>Content</p>",
            recipient_email="test@example.com",
            from_email="sender@example.com",
        )

        service._send_email(payload)

        mock_email_class.assert_called_once_with(
            subject="Test",
            body="Bitte verwende den HTML-Content",
            from_email="sender@example.com",
            to=["test@example.com"],
        )

    @patch("bewegungsradius.core.email.base.EmailMultiAlternatives")
    def test_send_email_attaches_html_alternative(self, mock_email_class, service):
        """_send_email fügt HTML Alternative an"""
        mock_email_instance = Mock()
        mock_email_class.return_value = mock_email_instance

        payload = EmailPayload(
            subject="Test",
            html_content="<p>HTML Content</p>",
            recipient_email="test@example.com",
        )

        service._send_email(payload)

        mock_email_instance.attach_alternative.assert_called_once_with(
            "<p>HTML Content</p>", "text/html"
        )

    @patch("bewegungsradius.core.email.base.EmailMultiAlternatives")
    def test_send_email_calls_send(self, mock_email_class, service):
        """_send_email ruft send() auf"""
        mock_email_instance = Mock()
        mock_email_class.return_value = mock_email_instance

        payload = EmailPayload(
            subject="Test",
            html_content="<p>Content</p>",
            recipient_email="test@example.com",
        )

        service._send_email(payload)

        mock_email_instance.send.assert_called_once()


# ==================== INTEGRATION TESTS ====================


class TestEmailServiceIntegration:
    """Integration Tests für Email-Workflow"""

    @pytest.fixture
    def service(self):
        """Service Fixture"""
        return ConcreteEmailService()

    @patch("bewegungsradius.core.email.base.render_to_string")
    @patch("bewegungsradius.core.email.base.EmailMultiAlternatives")
    def test_complete_email_workflow(self, mock_email_class, mock_render, service):
        """Kompletter Workflow: Template -> Payload -> Email"""
        mock_render.return_value = "<p>Rendered Content</p>"
        mock_email_instance = Mock()
        mock_email_class.return_value = mock_email_instance

        result = service.send_single_email(email="user@example.com")

        assert result is True
        mock_email_class.assert_called_once()
        mock_email_instance.send.assert_called_once()

    @patch("bewegungsradius.core.email.base.render_to_string")
    @patch("bewegungsradius.core.email.base.EmailMultiAlternatives")
    def test_bulk_workflow_with_mixed_results(
        self, mock_email_class, mock_render, service
    ):
        """Bulk Workflow mit Mix aus Success und Errors"""
        mock_render.return_value = "<p>Content</p>"
        mock_email_instance = Mock()
        mock_email_class.return_value = mock_email_instance

        # Zweiter Versand schlägt fehl
        mock_email_instance.send.side_effect = [None, Exception("Send failed"), None]

        recipients = [
            {"email": "user1@example.com"},
            {"email": "user2@example.com"},
            {"email": "user3@example.com"},
        ]

        result = service.send_bulk_emails(recipients)

        assert result["sent"] == 2
        assert result["errors"] == 1
