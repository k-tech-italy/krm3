import typing

from django.contrib.admin import site

if typing.TYPE_CHECKING:
    from django.http import HttpRequest


def admin_header(request: "HttpRequest") -> dict:
    """Add admin site header."""
    return {
        "admin_title": site.site_header
    }
