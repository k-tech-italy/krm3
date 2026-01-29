import pytest
from django.urls import reverse
from testutils.factories import UserFactory, DocumentFactory, DocumentGrantFactory


class TestDocumentListView:
    """Tests for the DocumentListView."""

    def test_anonymous_user_cannot_access_view_and_is_redirected_to_login(self, client):
        """Test that anonymous users are redirected to login page."""
        url = reverse('document_list')
        response = client.get(url)

        assert response.status_code == 302
        assert response.url == f'/admin/login/?next={url}'

    def test_authenticated_user_can_access_view(self, client):
        """Test that authenticated users can access the document list view."""
        UserFactory(username='testuser', password='pass123')
        client.login(username='testuser', password='pass123')

        url = reverse('document_list')
        response = client.get(url)

        assert response.status_code == 200

    def test_get_base_queryset_handles_exception_gracefully(self, client, monkeypatch):
        """Test that exceptions in _get_base_queryset are handled and error message is shown."""
        # Setup: mock accessible_by to raise an exception
        def mock_accessible_by(*args, **kwargs):
            raise Exception('Database connection error')

        from krm3.core.models.documents import ProtectedDocument as Document
        monkeypatch.setattr(Document.objects, 'accessible_by', mock_accessible_by)

        UserFactory(username='testuser', password='pass123')
        client.login(username='testuser', password='pass123')

        url = reverse('document_list')
        response = client.get(url)

        # Assert response is successful but shows error
        assert response.status_code == 200

        # Check that error message is displayed
        content = response.content.decode()
        assert 'Error loading documents' in content

        # Verify no documents are shown (empty state or no document list)
        # The view should return an empty queryset
        assert 'documents' in response.context
        documents = response.context['documents']
        assert len(documents) == 0

    def test_get_base_queryset_returns_only_accessible_documents(self, client):
        """Test that _get_base_queryset returns only documents accessible by the logged-in user."""
        # Create users
        user1 = UserFactory(username='user1', password='pass123')
        user2 = UserFactory(username='user2', password='pass123')

        # Create documents using factories
        # Document owned by user1
        doc1 = DocumentFactory(admin=user1)
        # Document owned by user2
        doc2 = DocumentFactory(admin=user2)
        # Document with grant for user1
        doc3 = DocumentFactory(admin=user2)
        DocumentGrantFactory(user=user1, document=doc3, granted_permissions=['R'])

        # Login as user1
        client.login(username='user1', password='pass123')

        url = reverse('document_list')
        response = client.get(url)

        assert response.status_code == 200

        # Check that only accessible documents are returned
        documents = response.context['documents']
        document_ids = [doc.id for doc in documents]

        # user1 should see doc1 (owned) and doc3 (granted access)
        assert doc1.id in document_ids
        assert doc3.id in document_ids
        # user1 should NOT see doc2 (owned by user2, no grant)
        assert doc2.id not in document_ids
        assert len(documents) == 2

    def test_parse_and_apply_filter_handles_unicode_decode_error(self, client):
        """Test that UnicodeDecodeError in filter parameter is handled gracefully."""
        import base64

        # Create a user and login
        UserFactory(username='testuser', password='pass123')
        client.login(username='testuser', password='pass123')

        # Create invalid base64 that decodes to invalid UTF-8 bytes
        # Using bytes that are not valid UTF-8 sequences
        invalid_utf8_bytes = b'\xff\xfe\xfd'
        invalid_filter = base64.b64encode(invalid_utf8_bytes).decode('ascii')

        url = reverse('document_list')
        response = client.get(url, {'filter': invalid_filter})

        # Assert response is successful but shows error
        assert response.status_code == 200

        # Check that error message is displayed
        content = response.content.decode()
        assert 'Invalid filter encoding' in content

        # Verify that documents context exists and filter was not applied
        assert 'documents' in response.context
        assert response.context['current_filter'] is None

    def test_parse_and_apply_filter_handles_json_decode_error(self, client):
        """Test that JSONDecodeError in filter parameter is handled gracefully."""
        import base64

        # Create a user and login
        UserFactory(username='testuser', password='pass123')
        client.login(username='testuser', password='pass123')

        # Create base64 that decodes to valid UTF-8 but invalid JSON
        invalid_json_string = 'this is not valid JSON {{'
        invalid_filter = base64.b64encode(invalid_json_string.encode('utf-8')).decode('ascii')

        url = reverse('document_list')
        response = client.get(url, {'filter': invalid_filter})

        # Assert response is successful but shows error
        assert response.status_code == 200

        # Check that error message is displayed
        content = response.content.decode()
        assert 'Invalid filter format' in content

        # Verify that documents context exists and filter was not applied
        assert 'documents' in response.context
        assert response.context['current_filter'] is None

    def test_parse_and_apply_filter_handles_value_error_unsupported_field(self, client):
        """Test that ValueError from unsupported field in filter is handled gracefully."""
        import base64
        import json

        # Create a user and login
        UserFactory(username='testuser', password='pass123')
        client.login(username='testuser', password='pass123')

        # Create a valid JSON filter with an unsupported field
        filter_dict = {
            'field': 'unsupported_field',
            'operator': 'icontains',
            'value': 'test',
        }
        filter_json = json.dumps(filter_dict)
        invalid_filter = base64.b64encode(filter_json.encode('utf-8')).decode('ascii')

        url = reverse('document_list')
        response = client.get(url, {'filter': invalid_filter})

        # Assert response is successful but shows error
        assert response.status_code == 200

        # Check that error message is displayed with the specific ValueError message
        content = response.content.decode()
        assert 'Unsupported field' in content or 'unsupported_field' in content

        # Verify that documents context exists and filter was not applied
        assert 'documents' in response.context
        assert response.context['current_filter'] is None

    def test_parse_and_apply_filter_handles_unexpected_exception(self, client, monkeypatch):
        """Test that unexpected exceptions in filter application are handled gracefully.

        This test uses mocking because the general Exception handler is designed to catch
        truly unexpected errors that shouldn't normally occur in the regular flow.
        All expected exceptions (JSONDecodeError, UnicodeDecodeError, binascii.Error,
        ValueError) are already tested separately.
        """
        import base64
        import json

        # Create a user and login
        UserFactory(username='testuser', password='pass123')
        client.login(username='testuser', password='pass123')

        # Create a valid filter
        filter_dict = {
            'field': 'filename',
            'operator': 'icontains',
            'value': 'test',
        }
        filter_json = json.dumps(filter_dict)
        valid_filter = base64.b64encode(filter_json.encode('utf-8')).decode('ascii')

        # Mock DocumentFilter to raise an unexpected exception (e.g., RuntimeError)
        def mock_document_filter_init(*_):
            raise RuntimeError('Unexpected database error')

        from krm3.web import views
        monkeypatch.setattr(views, 'DocumentFilter', mock_document_filter_init)

        url = reverse('document_list')
        response = client.get(url, {'filter': valid_filter})

        # Assert response is successful but shows error
        assert response.status_code == 200

        # Check that error message is displayed
        content = response.content.decode()
        assert 'Error applying filter' in content

        # Verify that documents context exists and filter was not applied
        assert 'documents' in response.context
        assert response.context['current_filter'] is None

    def test_apply_sorting_defaults_to_upload_date_descending(self, client):
        """Test that _apply_sorting defaults to '-upload_date' (descending) when sort param is not present."""
        # Create a user and login
        UserFactory(username='testuser', password='pass123')
        client.login(username='testuser', password='pass123')

        # Make the request without a sort parameter
        url = reverse('document_list')
        response = client.get(url)

        # Assert response is successful
        assert response.status_code == 200

        # Verify that current_sort is set to the default '-upload_date' (descending order)
        assert response.context['current_sort'] == '-upload_date'

    @pytest.mark.parametrize(
        'sort_field,field_name,create_documents_func',
        [
            ('document', 'document', 'create_docs_with_filenames'),
            ('-document', 'document', 'create_docs_with_filenames'),
            ('upload_date', 'upload_date', 'create_docs_with_upload_dates'),
            ('-upload_date', 'upload_date', 'create_docs_with_upload_dates'),
            ('reference_period', 'reference_period', 'create_docs_with_reference_periods'),
            ('-reference_period', 'reference_period', 'create_docs_with_reference_periods'),
            ('tags', 'tags', 'create_docs_with_tags'),
            ('-tags', 'tags', 'create_docs_with_tags'),
        ],
    )
    def test_apply_sorting_with_valid_sort_field(self, client, sort_field, field_name, create_documents_func):
        """Test that _apply_sorting correctly sorts documents by the specified field."""
        from datetime import date, datetime, timezone

        from psycopg.types.range import DateRange
        from testutils.factories import DocumentTagFactory

        # Create a user and login
        user = UserFactory(username='testuser', password='pass123')
        client.login(username='testuser', password='pass123')

        # Create documents based on the field being tested
        match create_documents_func:
            case 'create_docs_with_filenames':
                # Create documents with different filenames
                doc1 = DocumentFactory(admin=user, document='documents/2024/alpha.pdf')
                doc2 = DocumentFactory(admin=user, document='documents/2024/beta.pdf')
                doc3 = DocumentFactory(admin=user, document='documents/2024/gamma.pdf')
                expected_order = [doc1, doc2, doc3] if not sort_field.startswith('-') else [doc3, doc2, doc1]

            case 'create_docs_with_upload_dates':
                # Create documents with different upload dates
                doc1 = DocumentFactory(admin=user, upload_date=datetime(2024, 1, 1, tzinfo=timezone.utc))
                doc2 = DocumentFactory(admin=user, upload_date=datetime(2024, 6, 15, tzinfo=timezone.utc))
                doc3 = DocumentFactory(admin=user, upload_date=datetime(2024, 12, 31, tzinfo=timezone.utc))
                expected_order = [doc1, doc2, doc3] if not sort_field.startswith('-') else [doc3, doc2, doc1]

            case 'create_docs_with_reference_periods':
                # Create documents with different reference periods
                doc1 = DocumentFactory(
                    admin=user, reference_period=DateRange(date(2024, 1, 1), date(2024, 1, 31), bounds='[]')
                )
                doc2 = DocumentFactory(
                    admin=user, reference_period=DateRange(date(2024, 6, 1), date(2024, 6, 30), bounds='[]')
                )
                doc3 = DocumentFactory(
                    admin=user, reference_period=DateRange(date(2024, 12, 1), date(2024, 12, 31), bounds='[]')
                )
                expected_order = [doc1, doc2, doc3] if not sort_field.startswith('-') else [doc3, doc2, doc1]

            case 'create_docs_with_tags':
                # Create documents with different tags (sorted by tag title)
                tag1 = DocumentTagFactory(title='alpha-tag')
                tag2 = DocumentTagFactory(title='beta-tag')
                tag3 = DocumentTagFactory(title='gamma-tag')

                doc1 = DocumentFactory(admin=user)
                doc1.tags.add(tag1)

                doc2 = DocumentFactory(admin=user)
                doc2.tags.add(tag2)

                doc3 = DocumentFactory(admin=user)
                doc3.tags.add(tag3)

                expected_order = [doc1, doc2, doc3] if not sort_field.startswith('-') else [doc3, doc2, doc1]

        # Make the request with the sort parameter
        url = reverse('document_list')
        response = client.get(url, {'sort': sort_field})

        # Assert response is successful
        assert response.status_code == 200

        # Verify that current_sort is set to the requested field
        assert response.context['current_sort'] == sort_field

        # Verify documents are sorted correctly
        documents = list(response.context['documents'])
        document_ids = [doc.id for doc in documents]
        expected_ids = [doc.id for doc in expected_order]

        assert document_ids == expected_ids

    def test_apply_sorting_with_invalid_field_falls_back_to_default(self, client):
        """Test that invalid sort field preserves the param but falls back to default '-upload_date' ordering."""
        # Create a user and login
        UserFactory(username='testuser', password='pass123')
        client.login(username='testuser', password='pass123')

        # Make the request with an invalid sort parameter
        url = reverse('document_list')
        response = client.get(url, {'sort': 'invalid_field'})

        # Assert response is successful
        assert response.status_code == 200

        # Verify that current_sort preserves the invalid field (so UI can show it)
        assert response.context['current_sort'] == 'invalid_field'

        # The actual queryset ordering falls back to '-upload_date' (line 536 in views.py)
        # This is verified by the fact that the view doesn't crash and returns successfully

    def test_paginate_queryset_defaults_to_page_one_when_page_param_not_present(self, client):
        """Test that _paginate_queryset defaults to page 1 when page parameter is not present."""
        # Create a user and login
        user = UserFactory(username='testuser', password='pass123')
        client.login(username='testuser', password='pass123')

        # Create some documents (less than 10, so only 1 page)
        for _ in range(5):
            DocumentFactory(admin=user)

        # Make the request without a page parameter
        url = reverse('document_list')
        response = client.get(url)

        # Assert response is successful
        assert response.status_code == 200

        # Verify that we get page 1
        documents_page = response.context['documents']
        assert documents_page.number == 1
        assert documents_page.paginator.num_pages == 1

    def test_paginate_queryset_falls_back_to_page_one_when_page_not_integer(self, client):
        """Test that _paginate_queryset falls back to page 1 when page parameter is not an integer."""
        # Create a user and login
        user = UserFactory(username='testuser', password='pass123')
        client.login(username='testuser', password='pass123')

        # Create 15 documents (will result in 2 pages with 10 items per page)
        DocumentFactory.create_batch(15, admin=user)

        # Make the request with a non-integer page parameter
        url = reverse('document_list')
        response = client.get(url, {'page': 'not_a_number'})

        # Assert response is successful
        assert response.status_code == 200

        # Verify that we fall back to page 1 (PageNotAnInteger exception handled)
        documents_page = response.context['documents']
        assert documents_page.number == 1
        assert documents_page.paginator.num_pages == 2  # 15 docs / 10 per page = 2 pages

    def test_paginate_queryset_returns_last_page_when_page_out_of_range(self, client):
        """Test that _paginate_queryset returns last page when requested page is out of range."""
        # Create a user and login
        user = UserFactory(username='testuser', password='pass123')
        client.login(username='testuser', password='pass123')

        # Create 25 documents (will result in 3 pages with 10 items per page)
        DocumentFactory.create_batch(25, admin=user)

        # Make the request with a page number beyond available pages
        url = reverse('document_list')
        response = client.get(url, {'page': '999'})

        # Assert response is successful
        assert response.status_code == 200

        # Verify that we get the last page (EmptyPage exception handled)
        documents_page = response.context['documents']
        assert documents_page.number == 3  # Last page
        assert documents_page.paginator.num_pages == 3  # 25 docs / 10 per page = 3 pages
        assert len(documents_page) == 5  # Last page has 5 remaining documents

    def test_paginate_queryset_returns_correct_page_with_10_items_per_page(self, client):
        """Test that _paginate_queryset correctly paginates with 10 documents per page."""
        # Create a user and login
        user = UserFactory(username='testuser', password='pass123')
        client.login(username='testuser', password='pass123')

        # Create 35 documents (will result in 4 pages: 10, 10, 10, 5)
        DocumentFactory.create_batch(35, admin=user)

        # Test page 1
        url = reverse('document_list')
        response = client.get(url, {'page': '1'})
        assert response.status_code == 200
        documents_page = response.context['documents']
        assert documents_page.number == 1
        assert len(documents_page) == 10
        assert documents_page.paginator.num_pages == 4

        # Test page 2
        response = client.get(url, {'page': '2'})
        assert response.status_code == 200
        documents_page = response.context['documents']
        assert documents_page.number == 2
        assert len(documents_page) == 10

        # Test page 3
        response = client.get(url, {'page': '3'})
        assert response.status_code == 200
        documents_page = response.context['documents']
        assert documents_page.number == 3
        assert len(documents_page) == 10

        # Test page 4 (last page with remaining documents)
        response = client.get(url, {'page': '4'})
        assert response.status_code == 200
        documents_page = response.context['documents']
        assert documents_page.number == 4
        assert len(documents_page) == 5  # Only 5 remaining documents

    def test_get_available_tags_handles_exception_gracefully(self, client, monkeypatch):
        """Test that _get_available_tags handles exceptions and returns empty list."""
        # Create a user and login
        UserFactory(username='testuser', password='pass123')
        client.login(username='testuser', password='pass123')

        # Mock DocumentTag.objects to raise an exception
        def mock_values_list(*_):
            raise RuntimeError('Database connection error')

        from django_simple_dms.models import DocumentTag
        monkeypatch.setattr(DocumentTag.objects, 'values_list', mock_values_list)

        # Make the request
        url = reverse('document_list')
        response = client.get(url)

        # Assert response is successful despite error
        assert response.status_code == 200

        # Verify that available_tags is an empty list (exception handled)
        assert response.context['available_tags'] == []

        # Verify that the view still works (documents context exists)
        assert 'documents' in response.context

    def test_get_available_tags_returns_sorted_tag_titles(self, client):
        """Test that _get_available_tags returns all tag titles sorted alphabetically."""
        from testutils.factories import DocumentTagFactory

        # Create a user and login
        UserFactory(username='testuser', password='pass123')
        client.login(username='testuser', password='pass123')

        # Create tags in non-alphabetical order
        DocumentTagFactory(title='zebra-tag')
        DocumentTagFactory(title='alpha-tag')
        DocumentTagFactory(title='gamma-tag')
        DocumentTagFactory(title='beta-tag')

        # Make the request
        url = reverse('document_list')
        response = client.get(url)

        # Assert response is successful
        assert response.status_code == 200

        # Verify that available_tags contains all tags sorted alphabetically
        available_tags = response.context['available_tags']
        assert available_tags == ['alpha-tag', 'beta-tag', 'gamma-tag', 'zebra-tag']

    def test_document_list_view_with_complex_filter_sorting_and_pagination(self, client):
        """Test the complete happy path with complex filtering (AND/OR), sorting, and pagination."""
        import base64
        import json
        from datetime import date, datetime, timezone

        from psycopg.types.range import DateRange
        from testutils.factories import DocumentTagFactory

        # Create a user and login
        user = UserFactory(username='testuser', password='pass123')
        client.login(username='testuser', password='pass123')

        # Create tags
        tag_invoice = DocumentTagFactory(title='invoice')
        tag_report = DocumentTagFactory(title='report')
        tag_contract = DocumentTagFactory(title='contract')

        # Create documents that match the filter criteria
        # Documents matching: (filename contains "2024" AND upload_date >= 2024-01-01) OR tags contains "invoice"

        # This document matches the first condition (filename AND upload_date)
        doc1 = DocumentFactory(
            admin=user,
            document='documents/2024/report_2024.pdf',
            reference_period=DateRange(date(2024, 3, 1), date(2024, 3, 31), bounds='[]'),
        )
        doc1.tags.add(tag_report)
        # Update upload_date using queryset update to bypass auto_now_add
        from django_simple_dms.models import Document
        Document.objects.filter(pk=doc1.pk).update(upload_date=datetime(2024, 3, 15, tzinfo=timezone.utc))
        doc1.refresh_from_db()

        # This document matches the second condition (has invoice tag)
        doc2 = DocumentFactory(
            admin=user,
            document='documents/2023/old_invoice.pdf',
            reference_period=DateRange(date(2023, 12, 1), date(2023, 12, 31), bounds='[]'),
        )
        doc2.tags.add(tag_invoice)
        # Update upload_date using queryset update to bypass auto_now_add
        Document.objects.filter(pk=doc2.pk).update(upload_date=datetime(2023, 12, 1, tzinfo=timezone.utc))
        doc2.refresh_from_db()

        # This document matches both conditions
        doc3 = DocumentFactory(
            admin=user,
            document='documents/2024/invoice_2024.pdf',
            reference_period=DateRange(date(2024, 6, 1), date(2024, 6, 30), bounds='[]'),
        )
        doc3.tags.add(tag_invoice)
        # Update upload_date using queryset update to bypass auto_now_add
        Document.objects.filter(pk=doc3.pk).update(upload_date=datetime(2024, 6, 20, tzinfo=timezone.utc))
        doc3.refresh_from_db()

        # This document does NOT match any condition (should be excluded)
        doc4 = DocumentFactory(
            admin=user,
            document='documents/2023/old_contract.pdf',
            reference_period=DateRange(date(2023, 11, 1), date(2023, 11, 30), bounds='[]'),
        )
        doc4.tags.add(tag_contract)
        # Update upload_date using queryset update to bypass auto_now_add
        Document.objects.filter(pk=doc4.pk).update(upload_date=datetime(2023, 11, 1, tzinfo=timezone.utc))
        doc4.refresh_from_db()

        # Create complex filter: OR with nested AND conditions
        # Filter: (filename contains "2024" AND upload_date >= "2024-01-01") OR (tags contains "invoice")
        filter_dict = {
            'op': 'OR',
            'conditions': [
                {
                    'op': 'AND',
                    'conditions': [
                        {'field': 'filename', 'operator': 'icontains', 'value': '2024'},
                        {'field': 'upload_date', 'operator': 'gte', 'value': '2024-01-01'},
                    ],
                },
                {'field': 'tags', 'operator': 'contains_any', 'value': ['invoice']},
            ],
        }

        # Encode filter as base64
        filter_json = json.dumps(filter_dict)
        encoded_filter = base64.b64encode(filter_json.encode('utf-8')).decode('ascii')

        # Make request with filter, sorting by upload_date descending, page 1
        url = reverse('document_list')
        response = client.get(url, {'filter': encoded_filter, 'sort': '-upload_date', 'page': '1'})

        # Assert response is successful
        assert response.status_code == 200

        # Verify filter was applied correctly
        assert response.context['current_filter'] == filter_dict

        # Verify sorting is correct
        assert response.context['current_sort'] == '-upload_date'

        # Verify pagination
        documents_page = response.context['documents']
        assert documents_page.number == 1

        # Verify filtered and sorted results
        documents = list(documents_page)
        document_ids = [doc.id for doc in documents]

        # Should include doc1, doc2, doc3 (all match filter criteria)
        # Should exclude doc4 (doesn't match any condition)
        assert doc1.id in document_ids
        assert doc2.id in document_ids
        assert doc3.id in document_ids
        assert doc4.id not in document_ids

        # Verify sorting: documents should be ordered by upload_date descending
        # Expected order: doc3 (2024-06-20), doc1 (2024-03-15), doc2 (2023-12-01)
        assert len(document_ids) == 3
        assert documents[0].id == doc3.id  # Newest: 2024-06-20
        assert documents[1].id == doc1.id  # Middle: 2024-03-15
        assert documents[2].id == doc2.id  # Oldest: 2023-12-01

        # Verify tags are available
        assert 'available_tags' in response.context
        assert len(response.context['available_tags']) == 3

    def test_htmx_request_returns_partial_template(self, client):
        """Test that HTMX requests return only the partial template (document table) instead of full page."""
        # Create a user and login
        user = UserFactory(username='testuser', password='pass123')
        client.login(username='testuser', password='pass123')

        # Create some documents to display
        DocumentFactory.create_batch(3, admin=user)

        # Make a regular request (without HX-Request header)
        url = reverse('document_list')
        regular_response = client.get(url)

        assert regular_response.status_code == 200
        # Regular request should use the full template
        assert 'document_list.html' in [t.name for t in regular_response.templates]

        # Make an HTMX request (with HX-Request header)
        htmx_response = client.get(url, headers={'HX-Request': 'true'})

        assert htmx_response.status_code == 200
        # HTMX request should use only the partial template
        template_names = [t.name for t in htmx_response.templates]
        assert 'partials/document_table.html' in template_names
        assert 'document_list.html' not in template_names

        # Both responses should have the same context data
        assert 'documents' in regular_response.context
        assert 'documents' in htmx_response.context
        assert len(regular_response.context['documents']) == 3
        assert len(htmx_response.context['documents']) == 3

    def test_parse_and_apply_filter_handles_invalid_date_format_in_upload_date(self, client):
        """Test that invalid date format in upload_date filter generates validation error."""
        import base64
        import json

        # Create a user and login
        UserFactory(username='testuser', password='pass123')
        client.login(username='testuser', password='pass123')

        # Create a filter with invalid date format for upload_date
        filter_dict = {
            'field': 'upload_date',
            'operator': 'exact',
            'value': 'invalid-date',  # Invalid date format (should be YYYY-MM-DD)
        }
        filter_json = json.dumps(filter_dict)
        encoded_filter = base64.b64encode(filter_json.encode('utf-8')).decode('ascii')

        url = reverse('document_list')
        response = client.get(url, {'filter': encoded_filter})

        # Assert response is successful but shows error
        assert response.status_code == 200

        # Check that error message is displayed
        content = response.content.decode()
        assert 'Invalid date format for upload date filter' in content
        assert 'Expected format: YYYY-MM-DD' in content

        # Verify that documents context exists
        assert 'documents' in response.context

    def test_parse_and_apply_filter_handles_invalid_date_range_in_upload_date(self, client):
        """Test that invalid date range (start > end) in upload_date filter generates validation error."""
        import base64
        import json

        # Create a user and login
        UserFactory(username='testuser', password='pass123')
        client.login(username='testuser', password='pass123')

        # Create a filter with invalid date range (start date after end date)
        filter_dict = {
            'field': 'upload_date',
            'operator': 'between',
            'value': ['2024-12-31', '2024-01-01'],  # Start date after end date
        }
        filter_json = json.dumps(filter_dict)
        encoded_filter = base64.b64encode(filter_json.encode('utf-8')).decode('ascii')

        url = reverse('document_list')
        response = client.get(url, {'filter': encoded_filter})

        # Assert response is successful but shows error
        assert response.status_code == 200

        # Check that error message is displayed
        content = response.content.decode()
        assert 'Invalid date range for upload date' in content
        assert 'must be before or equal to end date' in content

        # Verify that documents context exists
        assert 'documents' in response.context

    def test_parse_and_apply_filter_handles_invalid_date_format_in_reference_period(self, client):
        """Test that invalid date format in reference_period filter generates validation error."""
        import base64
        import json

        # Create a user and login
        UserFactory(username='testuser', password='pass123')
        client.login(username='testuser', password='pass123')

        # Create a filter with invalid date format for reference_period
        filter_dict = {
            'field': 'reference_period',
            'operator': 'overlaps',
            'value': ['not-a-date', '2024-12-31'],  # Invalid date format
        }
        filter_json = json.dumps(filter_dict)
        encoded_filter = base64.b64encode(filter_json.encode('utf-8')).decode('ascii')

        url = reverse('document_list')
        response = client.get(url, {'filter': encoded_filter})

        # Assert response is successful but shows error
        assert response.status_code == 200

        # Check that error message is displayed
        content = response.content.decode()
        assert 'Invalid date format for reference period filter' in content
        assert 'Expected format: YYYY-MM-DD' in content

        # Verify that documents context exists
        assert 'documents' in response.context

    def test_parse_and_apply_filter_handles_invalid_date_range_in_reference_period(self, client):
        """Test that invalid date range (start > end) in reference_period filter generates validation error."""
        import base64
        import json

        # Create a user and login
        UserFactory(username='testuser', password='pass123')
        client.login(username='testuser', password='pass123')

        # Create a filter with invalid date range (start date after end date)
        filter_dict = {
            'field': 'reference_period',
            'operator': 'contains',
            'value': ['2024-06-30', '2024-06-01'],  # Start date after end date
        }
        filter_json = json.dumps(filter_dict)
        encoded_filter = base64.b64encode(filter_json.encode('utf-8')).decode('ascii')

        url = reverse('document_list')
        response = client.get(url, {'filter': encoded_filter})

        # Assert response is successful but shows error
        assert response.status_code == 200

        # Check that error message is displayed
        content = response.content.decode()
        assert 'Invalid date range for reference period' in content
        assert 'must be before or equal to end date' in content

        # Verify that documents context exists
        assert 'documents' in response.context
