"""Tests for protected media views.

These tests verify that the media views correctly:
- Require authentication (redirect to login if not authenticated)
- Return 404 for non-existent records
- Return 404 for records without files
- Return X-Accel-Redirect headers for valid files

NOTE: Currently, the views only check that the user is authenticated via @login_required.
In the future, proper permission checks should be added to verify that the requesting user
has permission to access the specific file (e.g., the expense belongs to their mission,
or they have the appropriate role to view the contract document).
"""

from unittest.mock import MagicMock

from django.conf import settings
from django.core.files import File
from django.urls import reverse
from testutils.factories import ContractFactory, ExpenseFactory


class TestServeExpenseImage:
    """Tests for the serve_expense_image view."""

    def test_unauthenticated_user_is_redirected_to_login(self, client, db):
        expense = ExpenseFactory()
        url = reverse('media-auth:expense-image', args=[expense.pk])

        response = client.get(url)

        assert response.status_code == 302
        assert '/login/' in response.url

    def test_returns_404_for_non_existent_expense(self, resource_client, db):
        url = reverse('media-auth:expense-image', args=[99999])

        response = resource_client.get(url)

        assert response.status_code == 404

    def test_returns_404_when_expense_has_no_image(self, resource_client, db):
        expense = ExpenseFactory(image=None)
        url = reverse('media-auth:expense-image', args=[expense.pk])

        response = resource_client.get(url)

        assert response.status_code == 404

    def test_returns_x_accel_redirect_for_valid_image(self, resource_client, db):
        filename = 'receipt.jpg'
        image = MagicMock(spec=File)
        image.name = filename
        expense = ExpenseFactory(image=image)

        url = reverse('media-auth:expense-image', args=[expense.pk])
        response = resource_client.get(url)

        assert response.status_code == 200
        assert 'X-Accel-Redirect' in response
        assert response['X-Accel-Redirect'] == f'{settings.PRIVATE_MEDIA_URL}{expense.image.name}'
        assert response['Content-Disposition'] == f'inline; filename="{expense.image.name.split("/")[-1]}"'


class TestServeContractDocument:
    """Tests for the serve_contract_document view."""

    def test_unauthenticated_user_is_redirected_to_login(self, client, db):
        contract = ContractFactory()
        url = reverse('media-auth:contract-document', args=[contract.pk])

        response = client.get(url)

        assert response.status_code == 302
        assert '/login/' in response.url

    def test_returns_404_for_non_existent_contract(self, resource_client, db):
        url = reverse('media-auth:contract-document', args=[99999])

        response = resource_client.get(url)

        assert response.status_code == 404

    def test_returns_404_when_contract_has_no_document(self, resource_client, db):
        contract = ContractFactory(document=None)
        url = reverse('media-auth:contract-document', args=[contract.pk])

        response = resource_client.get(url)

        assert response.status_code == 404

    def test_returns_x_accel_redirect_for_valid_document(self, resource_client, db):
        filename = 'contract.pdf'
        # Create contract first (without document) so it gets an ID
        contract = ContractFactory(document=None)

        # Create mock and assign document after contract has an ID
        document = MagicMock(spec=File)
        document.name = filename
        contract.document = document
        contract.save()

        url = reverse('media-auth:contract-document', args=[contract.pk])
        response = resource_client.get(url)

        assert response.status_code == 200
        assert 'X-Accel-Redirect' in response
        assert response['X-Accel-Redirect'] == f'{settings.PRIVATE_MEDIA_URL}{contract.document.name}'
        assert response['Content-Disposition'] == f'inline; filename="{contract.document.name.split("/")[-1]}"'
