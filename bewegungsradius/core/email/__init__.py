"""Email services - Base classes and utilities"""

from .base import BaseEmailService, EmailPayload, EmailTemplateConfig
from .exceptions import (EmailSendError, EmailServiceError,
                         EmailTemplateRenderError, EmailValidationError)

__all__ = [
    "BaseEmailService",
    "EmailPayload",
    "EmailTemplateConfig",
    "EmailServiceError",
    "EmailTemplateRenderError",
    "EmailValidationError",
    "EmailSendError",
]
