"""Custom exceptions for KRM3 core module."""


class PrivateMediaDirectUrlError(Exception):
    """Raised when attempting to access a private media file URL directly.

    Private media files should be accessed through model URL properties
    (e.g., contract.document_url, expense.image_url) that perform
    authentication and permission checks.
    """
