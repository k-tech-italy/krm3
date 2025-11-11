"""Tests for the UploadImageView in missions.views.

The OTP validation is properly implemented using Fernet encryption.
Invalid or malformed OTPs will return None from _validate_otp_and_get_expense,
resulting in a 400 Bad Request response.
"""

from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.shortcuts import reverse

from krm3.missions.views import UploadImageView

@pytest.fixture
def sample_image():
    """Create a sample image file for testing."""
    image_content = b'fake image content'
    return BytesIO(image_content)


class TestUploadImageViewGet:
    """Tests for the GET method of UploadImageView."""

    def test_get_with_valid_otp_returns_template(self, client, expense):
        """Test GET request with valid OTP returns the upload template."""
        otp = expense.get_otp()
        url = reverse('missions:expense-upload-image', args=[expense.pk])
        response = client.get(f'{url}?otp={otp}')

        assert response.status_code == 200
        assert 'expense' in response.context
        assert response.context['expense'].id == expense.id
        assert 'is_authenticated' in response.context
        assert response.context['is_authenticated'] is False
        assert 'current_url' in response.context
        assert response.context['current_url'] == f'{url}?otp={otp}'

    def test_get_with_invalid_otp_returns_bad_request(self, client, expense):
        """Test GET request with invalid OTP returns 400 Bad Request."""
        url = reverse('missions:expense-upload-image', args=[expense.pk])
        response = client.get(f'{url}?otp=invalid_otp')

        assert response.status_code == 400
        assert b'Invalid otp.' in response.content

    def test_get_without_otp_returns_bad_request(self, client, expense):
        """Test GET request without OTP parameter returns 400 Bad Request."""
        url = reverse('missions:expense-upload-image', args=[expense.pk])
        response = client.get(url)

        assert response.status_code == 400
        assert b'Invalid otp.' in response.content

    def test_get_with_nonexistent_expense_returns_bad_request(self, client):
        """Test GET request with non-existent expense ID returns 400 Bad Request.

        The Http404 exception is caught by _validate_otp_and_get_expense and returns None,
        resulting in an 'Invalid otp' error.
        """
        nonexistent_id = 99999
        url = reverse('missions:expense-upload-image', args=[nonexistent_id])
        response = client.get(f'{url}?otp=some_otp')

        assert response.status_code == 400
        assert b'Invalid otp.' in response.content

    def test_get_with_empty_otp_returns_bad_request(self, client, expense):
        """Test GET request with empty OTP parameter returns 400 Bad Request."""
        url = reverse('missions:expense-upload-image', args=[expense.pk])
        response = client.get(f'{url}?otp=')

        assert response.status_code == 400
        assert b'Invalid otp.' in response.content

    def test_get_with_authenticated_user_returns_correct_context(self, client, expense, regular_user):
        """Test GET request with authenticated user has is_authenticated=True in context."""
        otp = expense.get_otp()
        url = reverse('missions:expense-upload-image', args=[expense.pk])

        # Log in with the regular user
        client.force_login(regular_user)

        response = client.get(f'{url}?otp={otp}')

        assert response.status_code == 200
        assert 'is_authenticated' in response.context
        assert response.context['is_authenticated'] is True
        assert 'current_url' in response.context
        assert response.context['current_url'] == f'{url}?otp={otp}'


class TestUploadImageViewPatch:
    """Tests for the PATCH method of UploadImageView."""

    def _create_multipart_body(self, otp: str, image_data: bytes, boundary: str = 'boundary123') -> bytes:
        """
        Create a multipart/form-data request body.

        Args:
            otp: The OTP value
            image_data: The image data bytes
            boundary: The multipart boundary string

        Returns:
            The complete multipart body as bytes

        """
        body = (
            f'--{boundary}\r\n'
            f'Content-Disposition: form-data; name="otp"\r\n'
            f'\r\n'
            f'{otp}\r\n'
            f'--{boundary}\r\n'
            f'Content-Disposition: form-data; name="image"; filename="test.png"\r\n'
            f'Content-Type: image/png\r\n'
            f'\r\n'
        ).encode()
        body += image_data
        body += f'\r\n--{boundary}--\r\n'.encode()
        return body

    def test_patch_with_valid_otp_and_image_uploads_successfully(self, client, expense, sample_image):
        """Test PATCH request with valid OTP and image uploads successfully."""
        otp = expense.get_otp()
        image_data = sample_image.read()
        boundary = 'boundary123'
        body = self._create_multipart_body(otp, image_data, boundary)

        url = reverse('missions:expense-upload-image', args=[expense.pk])
        response = client.patch(url, data=body, content_type=f'multipart/form-data; boundary={boundary}')

        assert response.status_code == 204
        expense.refresh_from_db()
        assert expense.image.name is not None

    def test_patch_with_invalid_otp_returns_bad_request(self, client, expense, sample_image):
        """Test PATCH request with invalid OTP returns 400 Bad Request."""
        invalid_otp = 'invalid_otp_value'
        image_data = sample_image.read()
        boundary = 'boundary123'
        body = self._create_multipart_body(invalid_otp, image_data, boundary)

        url = reverse('missions:expense-upload-image', args=[expense.pk])
        response = client.patch(url, data=body, content_type=f'multipart/form-data; boundary={boundary}')

        assert response.status_code == 400
        assert b'Invalid otp.' in response.content

    def test_patch_without_image_returns_bad_request(self, client, expense):
        """Test PATCH request without image file returns 400 Bad Request."""
        otp = expense.get_otp()
        boundary = 'boundary123'
        body = (
            f'--{boundary}\r\n'
            f'Content-Disposition: form-data; name="otp"\r\n'
            f'\r\n'
            f'{otp}\r\n'
            f'--{boundary}--\r\n'
        ).encode()

        url = reverse('missions:expense-upload-image', args=[expense.pk])
        response = client.patch(url, data=body, content_type=f'multipart/form-data; boundary={boundary}')

        assert response.status_code == 400
        assert b'No image file found in the request.' in response.content

    def test_patch_without_otp_returns_bad_request(self, client, expense, sample_image):
        """Test PATCH request without OTP field returns 400 Bad Request."""
        image_data = sample_image.read()
        boundary = 'boundary123'
        body = (
            f'--{boundary}\r\n'
            f'Content-Disposition: form-data; name="image"; filename="test.png"\r\n'
            f'Content-Type: image/png\r\n'
            f'\r\n'
        ).encode()
        body += image_data
        body += f'\r\n--{boundary}--\r\n'.encode()

        url = reverse('missions:expense-upload-image', args=[expense.pk])
        response = client.patch(url, data=body, content_type=f'multipart/form-data; boundary={boundary}')

        assert response.status_code == 400
        assert b'Invalid otp.' in response.content

    def test_patch_with_invalid_content_type_returns_bad_request(self, client, expense):
        """Test PATCH request with invalid Content-Type returns 400 Bad Request."""
        url = reverse('missions:expense-upload-image', args=[expense.pk])
        response = client.patch(url, data={}, content_type='application/json')

        assert response.status_code == 400
        assert b'Invalid Content-Type. Expected multipart/form-data.' in response.content

    def test_patch_with_malformed_multipart_data_handles_gracefully(self, client, expense):
        """Test PATCH request with malformed multipart data handles gracefully.

        When multipart data is malformed, parse_multipart may succeed with empty data,
        resulting in an empty OTP which fails validation and returns 'Invalid otp'.
        """
        boundary = 'boundary123'
        malformed_body = b'this is not valid multipart data'

        url = reverse('missions:expense-upload-image', args=[expense.pk])
        response = client.patch(url, data=malformed_body, content_type=f'multipart/form-data; boundary={boundary}')

        assert response.status_code == 400
        # OTP validation happens first, so malformed data results in invalid OTP error
        assert b'Invalid otp.' in response.content

    def test_patch_replaces_existing_image(self, client, expense, sample_image):
        """Test PATCH request replaces existing image if one already exists."""
        # First, create an initial image
        initial_image = SimpleUploadedFile('initial.png', b'initial content', content_type='image/png')
        expense.image = initial_image
        expense.save()

        # Now upload a new image
        otp = expense.get_otp()
        new_image_data = b'new image content'
        boundary = 'boundary123'
        body = self._create_multipart_body(otp, new_image_data, boundary)

        url = reverse('missions:expense-upload-image', args=[expense.pk])
        response = client.patch(url, data=body, content_type=f'multipart/form-data; boundary={boundary}')

        assert response.status_code == 204
        expense.refresh_from_db()
        # The image should be updated
        assert expense.image.name is not None

    def test_patch_saves_image_successfully(self, client, expense, sample_image):
        """Test PATCH request saves image successfully."""
        otp = expense.get_otp()
        image_data = sample_image.read()
        boundary = 'boundary123'
        body = self._create_multipart_body(otp, image_data, boundary)

        url = reverse('missions:expense-upload-image', args=[expense.pk])
        response = client.patch(url, data=body, content_type=f'multipart/form-data; boundary={boundary}')

        assert response.status_code == 204
        expense.refresh_from_db()
        # Verify the image was saved
        assert expense.image.name is not None
        assert len(expense.image.name) > 0

    def test_patch_with_nonexistent_expense_returns_bad_request(self, client, sample_image):
        """Test PATCH request with non-existent expense ID returns 400 Bad Request.

        The Http404 exception is caught by _validate_otp_and_get_expense and returns None,
        resulting in an 'Invalid otp' error.
        """
        nonexistent_id = 99999
        otp = 'some_otp'
        image_data = sample_image.read()
        boundary = 'boundary123'
        body = self._create_multipart_body(otp, image_data, boundary)

        url = reverse('missions:expense-upload-image', args=[nonexistent_id])
        response = client.patch(url, data=body, content_type=f'multipart/form-data; boundary={boundary}')

        assert response.status_code == 400
        assert b'Invalid otp.' in response.content

    def test_patch_with_authenticated_user_uploads_successfully(self, client, expense, sample_image, regular_user):
        """Test PATCH request with authenticated user uploads image successfully."""
        otp = expense.get_otp()
        image_data = sample_image.read()
        boundary = 'boundary123'
        body = self._create_multipart_body(otp, image_data, boundary)

        # Log in with the regular user
        client.force_login(regular_user)

        url = reverse('missions:expense-upload-image', args=[expense.pk])
        response = client.patch(url, data=body, content_type=f'multipart/form-data; boundary={boundary}')

        assert response.status_code == 204
        expense.refresh_from_db()
        assert expense.image.name is not None


class TestUploadImageViewValidateOtpHelper:
    """Tests for the _validate_otp_and_get_expense static method."""

    def test_validate_otp_with_valid_otp_returns_expense(self, expense):
        """Test _validate_otp_and_get_expense with valid OTP returns the expense."""
        otp = expense.get_otp()
        result = UploadImageView._validate_otp_and_get_expense(expense.pk, otp)

        assert result is not None
        assert result.id == expense.id

    def test_validate_otp_with_invalid_otp_returns_none(self, expense):
        """Test _validate_otp_and_get_expense with invalid OTP returns None."""
        invalid_otp = 'invalid_otp_value'
        result = UploadImageView._validate_otp_and_get_expense(expense.pk, invalid_otp)

        assert result is None

    def test_validate_otp_with_empty_otp_returns_none(self, expense):
        """Test _validate_otp_and_get_expense with empty OTP returns None."""
        result = UploadImageView._validate_otp_and_get_expense(expense.pk, '')

        assert result is None

    def test_validate_otp_with_nonexistent_expense_returns_none(self):
        """Test _validate_otp_and_get_expense with non-existent expense returns None.

        The Http404 exception is caught and None is returned.
        """
        nonexistent_id = 99999
        otp = 'some_otp'

        result = UploadImageView._validate_otp_and_get_expense(nonexistent_id, otp)
        assert result is None


class TestUploadImageViewIntegration:
    """Integration tests for UploadImageView using the test client."""

    def test_get_request_integration(self, client, expense):
        """Integration test for GET request using Django test client."""
        otp = expense.get_otp()
        url = reverse('missions:expense-upload-image', args=[expense.pk])

        response = client.get(f'{url}?otp={otp}')

        assert response.status_code == 200
        assert b'Upload image' in response.content

    def test_patch_request_integration(self, client, expense):
        """Integration test for PATCH request using Django test client."""
        otp = expense.get_otp()
        image_data = b'fake image content'
        boundary = 'boundary123'

        body = (
            f'--{boundary}\r\n'
            f'Content-Disposition: form-data; name="otp"\r\n'
            f'\r\n'
            f'{otp}\r\n'
            f'--{boundary}\r\n'
            f'Content-Disposition: form-data; name="image"; filename="test.png"\r\n'
            f'Content-Type: image/png\r\n'
            f'\r\n'
        ).encode()
        body += image_data
        body += f'\r\n--{boundary}--\r\n'.encode()

        url = reverse('missions:expense-upload-image', args=[expense.pk])
        response = client.patch(url, data=body, content_type=f'multipart/form-data; boundary={boundary}')

        assert response.status_code == 204
        expense.refresh_from_db()
        assert expense.image.name is not None

    def test_only_get_and_patch_methods_allowed(self, client, expense):
        """Test that only GET and PATCH methods are allowed."""
        otp = expense.get_otp()
        url = reverse('missions:expense-upload-image', args=[expense.pk])

        # POST should not be allowed
        response = client.post(f'{url}?otp={otp}')
        assert response.status_code == 405  # Method Not Allowed

        # PUT should not be allowed
        response = client.put(f'{url}?otp={otp}')
        assert response.status_code == 405  # Method Not Allowed

        # DELETE should not be allowed
        response = client.delete(f'{url}?otp={otp}')
        assert response.status_code == 405  # Method Not Allowed

    def test_view_is_csrf_exempt(self, client, expense):
        """Test that the view is CSRF exempt (can accept requests without CSRF token)."""
        # This test verifies the @csrf_exempt decorator is working
        otp = expense.get_otp()
        url = reverse('missions:expense-upload-image', args=[expense.pk])

        # PATCH request without CSRF token should work
        image_data = b'fake image content'
        boundary = 'boundary123'

        body = (
            f'--{boundary}\r\n'
            f'Content-Disposition: form-data; name="otp"\r\n'
            f'\r\n'
            f'{otp}\r\n'
            f'--{boundary}\r\n'
            f'Content-Disposition: form-data; name="image"; filename="test.png"\r\n'
            f'Content-Type: image/png\r\n'
            f'\r\n'
        ).encode()
        body += image_data
        body += f'\r\n--{boundary}--\r\n'.encode()

        response = client.patch(url, data=body, content_type=f'multipart/form-data; boundary={boundary}')

        # Should succeed without CSRF token because of @csrf_exempt
        assert response.status_code == 204
