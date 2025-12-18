"""
core/email/exceptions.py - Custom Exceptions
=============================================
"""


class EmailServiceError(Exception):
    """Basis Exception für Email Services"""
    pass


class EmailTemplateRenderError(EmailServiceError):
    """Template Rendering ist fehlgeschlagen"""
    pass


class EmailValidationError(EmailServiceError):
    """Email Validierung ist fehlgeschlagen"""
    pass


class EmailSendError(EmailServiceError):
    """Email Versand ist fehlgeschlagen"""
    pass