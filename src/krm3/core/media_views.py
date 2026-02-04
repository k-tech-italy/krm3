"""Views for serving protected media files via nginx X-Accel-Redirect.

These views handle authentication and authorization for private media files.
After validating access, they return an X-Accel-Redirect header that instructs
nginx to serve the actual file from the internal location.

The nginx configuration should have an internal location block like:
    location /protected-media/ {
        internal;
        alias /path/to/private/media/;
    }
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponse

from krm3.core.models.documents import ProtectedDocument as Document

from krm3.core.models import Contract, Expense

if TYPE_CHECKING:
    from django.db.models import Model
    from django.db.models.fields.files import FieldFile
    from django.http import HttpRequest

    from krm3.core.models import User

logger = logging.getLogger(__name__)


def _get_object_with_permission_check(
    model_class: type['Model'],
    pk: int,
    user: 'User',
) -> 'Model':
    """Get object after verifying user has access via accessible_by.

    This function first checks if the object exists, then verifies that
    the user has permission to access it using the model's accessible_by method.

    Args:
        model_class: The Django model class to query
        pk: The primary key of the object to retrieve
        user: The user requesting access

    Returns:
        The model instance if found and accessible

    Raises:
        Http404: If the object doesn't exist
        PermissionDenied: If the user doesn't have permission to access the object

    """
    # First check if object exists at all
    if not model_class.objects.filter(pk=pk).exists():
        raise Http404('Object not found')

    # Try to get it through accessible_by
    try:
        return model_class.objects.accessible_by(user).get(pk=pk)
    except model_class.DoesNotExist:
        raise PermissionDenied("You don't have permission to access this file.")


def _serve_protected_file(file_field: FieldFile | None, request: HttpRequest) -> HttpResponse:
    """Create an X-Accel-Redirect response for a file field.

    Args:
        file_field: Django FileField with the file to serve
        request: The HTTP request

    Returns:
        HttpResponse with X-Accel-Redirect header

    Raises:
        Http404: If the file field is empty

    """
    if file_field is None or not file_field.name:
        raise Http404('File not found')

    # Get the relative path from the file field
    relative_path: str = file_field.name

    # Log the access
    logger.info(
        'Protected media access: user=%s, file=%s, ip=%s',
        getattr(request.user, 'username', 'unknown'),
        relative_path,
        request.META.get('REMOTE_ADDR', 'unknown'),
    )

    # Build the X-Accel-Redirect URL
    # PRIVATE_MEDIA_URL should be something like '/protected-media/'
    redirect_url = f'{settings.PRIVATE_MEDIA_URL}{relative_path}'

    # Get the filename for Content-Disposition
    filename = Path(relative_path).name


    # Create the response with X-Accel-Redirect
    # this headers tells nginx to serve the file
    # see docker/etc/sites-available/krm3.conf.template for nginx configuration
    response = HttpResponse()
    response['X-Accel-Redirect'] = redirect_url
    response['Content-Disposition'] = f'inline; filename="{filename}"'

    # Remove Content-Type to let nginx determine it from the file extension
    # nginx will use its mime.types to set the correct Content-Type
    del response['Content-Type']

    return response


@login_required
def serve_expense_image(request: HttpRequest, expense_id: int) -> HttpResponse:
    """Serve an expense image file via nginx X-Accel-Redirect.

    URL: /media-auth/expenses/<expense_id>/

    Args:
        request: The HTTP request
        expense_id: The ID of the Expense record

    Returns:
        HttpResponse with X-Accel-Redirect header pointing to the file

    Raises:
        Http404: If expense not found or has no image
        PermissionDenied: If user doesn't have permission to access the expense

    """
    expense = _get_object_with_permission_check(Expense, expense_id, request.user)
    return _serve_protected_file(expense.image, request)


@login_required
def serve_contract_document(request: HttpRequest, contract_id: int) -> HttpResponse:
    """Serve a contract document file via nginx X-Accel-Redirect.

    URL: /media-auth/contracts/<contract_id>/

    Args:
        request: The HTTP request
        contract_id: The ID of the Contract record

    Returns:
        HttpResponse with X-Accel-Redirect header pointing to the file

    Raises:
        Http404: If contract not found or has no document
        PermissionDenied: If user doesn't have permission to access the contract

    """
    contract = _get_object_with_permission_check(Contract, contract_id, request.user)
    return _serve_protected_file(contract.document, request)


@login_required
def serve_document_file(request: HttpRequest, document_id: int) -> HttpResponse:
    """Serve a DMS document file via nginx X-Accel-Redirect.

    URL: /media-auth/documents/<document_id>/

    Args:
        request: The HTTP request
        document_id: The ID of the Document record

    Returns:
        HttpResponse with X-Accel-Redirect header pointing to the file

    Raises:
        Http404: If document not found or has no file
        PermissionDenied: If user doesn't have permission to access the document

    """
    doc = _get_object_with_permission_check(Document, document_id, request.user)
    return _serve_protected_file(doc.document, request)
