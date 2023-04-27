from django.db.backends.postgresql import base as original_backend

from .creation import DatabaseCreation


class DatabaseWrapper(original_backend.DatabaseWrapper):
    """
    Adds the capability to automatically create the test_krm3.django schema
    """
    include_public_schema = True
    creation_class = DatabaseCreation
