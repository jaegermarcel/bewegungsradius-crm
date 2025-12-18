"""Email services - Base classes and utilities"""

from .base import BaseEmailService, EmailPayload, EmailTemplateConfig
from .exceptions import EmailServiceError, EmailTemplateRenderError, EmailValidationError, EmailSendError

__all__ = [
    'BaseEmailService',
    'EmailPayload',
    'EmailTemplateConfig',
    'EmailServiceError',
    'EmailTemplateRenderError',
    'EmailValidationError',
    'EmailSendError',
]