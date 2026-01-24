"""Tests for custom form widgets."""

from unittest.mock import MagicMock

import pytest

from krm3.core.widgets import PrivateMediaFileInput


class TestPrivateMediaFileInput:
    """Tests for the PrivateMediaFileInput widget."""

    def test_render_without_file_returns_file_input(self):
        """When no file exists, widget renders a simple file input."""
        widget = PrivateMediaFileInput(url_field='document_url')

        html = widget.render('document', None)

        assert '<input type="file"' in html
        assert 'Currently:' not in html
        assert 'Clear' not in html

    def test_render_with_file_shows_current_link_and_clear_checkbox(self):
        """When file exists with URL, widget renders link, clear checkbox, and file input."""
        widget = PrivateMediaFileInput(url_field='document_url')
        widget.is_required = False

        # Create a mock FieldFile with an instance that has the url_field
        mock_instance = MagicMock()
        mock_instance.document_url = '/media-auth/contracts/1/'

        mock_file = MagicMock()
        mock_file.instance = mock_instance
        mock_file.name = 'contracts/documents/R1/C1/contract.pdf'

        html = widget.render('document', mock_file)

        # Check for current file link
        assert 'Currently:' in html
        assert '<a href="/media-auth/contracts/1/">' in html
        assert 'contract.pdf</a>' in html

        # Check for clear checkbox (since is_required=False)
        assert '<input type="checkbox" name="document-clear"' in html
        assert '<label for="document-clear_id">Clear</label>' in html

        # Check for file input
        assert 'Change:' in html
        assert '<input type="file"' in html

    def test_render_with_file_required_hides_clear_checkbox(self):
        """When widget is required, clear checkbox is not shown."""
        widget = PrivateMediaFileInput(url_field='document_url')
        widget.is_required = True

        mock_instance = MagicMock()
        mock_instance.document_url = '/media-auth/contracts/1/'

        mock_file = MagicMock()
        mock_file.instance = mock_instance
        mock_file.name = 'contract.pdf'

        html = widget.render('document', mock_file)

        # Should have the link but no clear checkbox
        assert 'Currently:' in html
        assert '<a href="/media-auth/contracts/1/">' in html
        assert 'Clear' not in html
        assert 'Change:' in html

    def test_render_extracts_filename_from_path(self):
        """Widget extracts just the filename from the full path for display."""
        widget = PrivateMediaFileInput(url_field='image_url')
        widget.is_required = False

        mock_instance = MagicMock()
        mock_instance.image_url = '/media-auth/expenses/123/'

        mock_file = MagicMock()
        mock_file.instance = mock_instance
        mock_file.name = 'missions/expenses/R1/M1/receipt.jpg'

        html = widget.render('image', mock_file)

        # Should show just the filename, not the full path
        assert 'receipt.jpg</a>' in html
        assert 'missions/expenses/R1/M1/receipt.jpg</a>' not in html

    def test_init_stores_url_field(self):
        """Widget stores the url_field parameter."""
        widget = PrivateMediaFileInput(url_field='my_custom_url')

        assert widget.url_field == 'my_custom_url'

    def test_init_accepts_attrs(self):
        """Widget accepts HTML attributes."""
        widget = PrivateMediaFileInput(url_field='document_url', attrs={'class': 'custom-class'})

        assert widget.attrs.get('class') == 'custom-class'

    def test_render_with_value_without_instance_attribute(self):
        """When value exists but has no instance attribute, renders simple file input."""
        widget = PrivateMediaFileInput(url_field='document_url')

        # A simple string value that has no 'instance' attribute
        html = widget.render('document', 'some_file.pdf')

        assert '<input type="file"' in html
        assert 'Currently:' not in html

    def test_render_with_file_but_instance_missing_url_field(self):
        """When instance doesn't have the url_field property, renders simple file input."""
        widget = PrivateMediaFileInput(url_field='nonexistent_url')

        # Create a mock file with an instance that doesn't have the url_field
        class MockInstance:
            # No nonexistent_url attribute here
            pass

        class MockFile:
            instance = MockInstance()
            name = 'contract.pdf'

        html = widget.render('document', MockFile())

        assert '<input type="file"' in html
        assert 'Currently:' not in html

    @pytest.mark.parametrize('url_value', [None, ''])
    def test_render_with_file_but_url_is_falsy(self, url_value):
        """When file exists but URL property returns falsy value, renders simple file input."""
        widget = PrivateMediaFileInput(url_field='document_url')

        class MockInstance:
            document_url = url_value

        class MockFile:
            instance = MockInstance()
            name = 'contract.pdf'

        html = widget.render('document', MockFile())

        assert '<input type="file"' in html
        assert 'Currently:' not in html

    def test_get_context_with_valid_file_sets_relative_url(self):
        """get_context sets the relative URL in context when file has valid url_field."""
        widget = PrivateMediaFileInput(url_field='document_url')

        class MockInstance:
            document_url = '/media-auth/contracts/1/'

        class MockFile:
            instance = MockInstance()
            name = 'contract.pdf'

        mock_file = MockFile()
        context = widget.get_context('document', mock_file, {})

        assert context['widget']['url'] == '/media-auth/contracts/1/'

    def test_get_context_without_url_field_does_not_set_url(self):
        """get_context does not set URL when instance lacks url_field."""
        widget = PrivateMediaFileInput(url_field='nonexistent_url')

        class MockInstance:
            pass

        class MockFile:
            instance = MockInstance()
            name = 'contract.pdf'

        context = widget.get_context('document', MockFile(), {})

        # URL should not be in context (or should be the default from parent)
        assert context['widget'].get('url') is None or 'media-auth' not in str(context['widget'].get('url', ''))

    def test_get_context_with_none_url_does_not_override(self):
        """get_context does not set URL when url_field returns None."""
        widget = PrivateMediaFileInput(url_field='document_url')

        class MockInstance:
            document_url = None

        class MockFile:
            instance = MockInstance()
            name = 'contract.pdf'

        context = widget.get_context('document', MockFile(), {})

        # URL should not be set to our custom URL
        assert context['widget'].get('url') is None or 'media-auth' not in str(context['widget'].get('url', ''))
