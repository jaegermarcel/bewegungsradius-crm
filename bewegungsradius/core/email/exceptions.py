"""
core/email/exceptions.py - Custom Exceptions
=============================================
"""


class EmailServiceError(Exception):
    """Basis Exception für Email Services"""


class EmailTemplateRenderError(EmailServiceError):
    """Template Rendering ist fehlgeschlagen"""


class EmailValidationError(EmailServiceError):
    """Email Validierung ist fehlgeschlagen"""


class EmailSendError(EmailServiceError):
    """Email Versand ist fehlgeschlagen"""
