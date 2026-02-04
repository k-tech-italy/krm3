"""Tests for ProtectedDocument proxy model."""

from unittest.mock import MagicMock

from django.core.files import File
from django.urls import reverse
from testutils.factories import DocumentFactory

from krm3.core.models import ProtectedDocument


class TestProtectedDocumentFileUrl:
    """Tests for the file_url property."""

    def test_file_url_returns_none_when_no_file(self, db):
        doc = DocumentFactory(document=None)
        protected_doc = ProtectedDocument.objects.get(pk=doc.pk)

        assert protected_doc.file_url is None

    def test_file_url_returns_authenticated_url_when_file_exists(self, db):
        doc = DocumentFactory()
        protected_doc = ProtectedDocument.objects.get(pk=doc.pk)

        expected_url = reverse('media-auth:document-file', args=[protected_doc.pk])
        assert protected_doc.file_url == expected_url

    def test_file_url_with_mock_file(self, db):
        document_file = MagicMock(spec=File)
        document_file.name = 'documents/test.pdf'
        doc = DocumentFactory(document=document_file)
        protected_doc = ProtectedDocument.objects.get(pk=doc.pk)

        expected_url = reverse('media-auth:document-file', args=[protected_doc.pk])
        assert protected_doc.file_url == expected_url
