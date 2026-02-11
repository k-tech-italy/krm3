"""Tests for ProtectedDocument proxy model."""

from contextlib import nullcontext as does_not_raise
from unittest.mock import MagicMock

from django.core.files import File
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from testutils.factories import DocumentFactory

from krm3.core.models import ProtectedDocument


class TestProtectedDocument:
    """Tests for the ProtectedDocument proxy model."""

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

    def test_file_deleted_from_storage_on_model_delete(self, db):
        doc = DocumentFactory()
        storage = doc.document.storage
        file_name = doc.document.name

        assert storage.exists(file_name)

        doc.delete()

        assert not storage.exists(file_name)

    def test_no_error_when_deleting_document_without_file(self, db):
        doc = DocumentFactory(document=None)
        doc.delete()  # should not raise

    def test_old_file_deleted_when_file_replaced(self, db):
        doc = DocumentFactory()
        storage = doc.document.storage
        old_file_name = doc.document.name

        assert storage.exists(old_file_name)

        doc.document = SimpleUploadedFile('new_document.txt', b'new content')
        doc.save()

        assert not storage.exists(old_file_name)
        assert storage.exists(doc.document.name)

    def test_no_error_when_saving_with_pk_not_in_db(self, db):
        doc = ProtectedDocument(pk=99999, document=SimpleUploadedFile('test.txt', b'content'))
        with does_not_raise():
            doc.save()
        assert ProtectedDocument.objects.filter(pk=99999).exists()
        assert doc.document.storage.exists(doc.document.name)

    def test_file_not_deleted_when_saving_without_change(self, db):
        doc = DocumentFactory()
        storage = doc.document.storage
        file_name = doc.document.name

        doc.save()

        assert storage.exists(file_name)
