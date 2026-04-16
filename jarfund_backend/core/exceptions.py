"""
Custom exception handler — ensures all API errors return a consistent
JSON envelope:

    {
        "success": false,
        "error": {
            "code":    "validation_error",
            "message": "Human-readable summary",
            "details": { ... }   // field-level errors when available
        }
    }
"""
import logging

from django.core.exceptions import PermissionDenied
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import (
    APIException,
    AuthenticationFailed,
    NotAuthenticated,
    ValidationError,
)
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Call DRF's default handler first, then reformat the response
    into our standard error envelope.
    """
    # Convert Django's Http404 and PermissionDenied to DRF equivalents
    if isinstance(exc, Http404):
        exc = APIException("Resource not found.")
        exc.status_code = status.HTTP_404_NOT_FOUND
        exc.default_code = "not_found"

    elif isinstance(exc, PermissionDenied):
        exc = APIException("You do not have permission to perform this action.")
        exc.status_code = status.HTTP_403_FORBIDDEN
        exc.default_code = "permission_denied"

    response = exception_handler(exc, context)

    if response is not None:
        error_code    = getattr(exc, "default_code", "error")
        error_details = None

        # ValidationError has field-level detail
        if isinstance(exc, ValidationError):
            error_code    = "validation_error"
            error_details = response.data  # field -> [errors]
            message       = "One or more fields failed validation."
        else:
            message = _extract_message(response.data)

        response.data = {
            "success": False,
            "error": {
                "code":    error_code,
                "message": message,
                **({"details": error_details} if error_details else {}),
            },
        }

        # Log 5xx errors
        if response.status_code >= 500:
            logger.error(
                "Server error: %s — %s",
                response.status_code,
                message,
                exc_info=exc,
            )

    return response


def _extract_message(data) -> str:
    """Flatten DRF's varied error structure into a single message string."""
    if isinstance(data, dict):
        # e.g. {"detail": "Not found."}
        if "detail" in data:
            return str(data["detail"])
        # Take first field's first error
        for _field, errors in data.items():
            if isinstance(errors, list) and errors:
                return str(errors[0])
            return str(errors)
    if isinstance(data, list) and data:
        return str(data[0])
    return str(data)
