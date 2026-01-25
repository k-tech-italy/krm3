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
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404

from krm3.core.models import Contract, Expense

if TYPE_CHECKING:
    from django.db.models.fields.files import FieldFile
    from django.http import HttpRequest

logger = logging.getLogger(__name__)


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

    """
    expense = get_object_or_404(Expense, pk=expense_id)
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

    """
    contract = get_object_or_404(Contract, pk=contract_id)
    return _serve_protected_file(contract.document, request)
