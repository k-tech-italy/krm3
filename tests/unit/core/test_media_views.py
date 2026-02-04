"""Tests for protected media views.

These tests verify that the media views correctly:
- Require authentication (redirect to login if not authenticated)
- Return 404 for non-existent records
- Return 404 for records without files
- Return 403 for users without permission
- Return X-Accel-Redirect headers for valid files when user has permission
"""

from unittest.mock import MagicMock

from django.conf import settings
from django.core.files import File
from django.urls import reverse
from testutils.factories import (
    ContractFactory,
    DocumentFactory,
    DocumentGrantFactory,
    ExpenseFactory,
    GroupFactory,
    MissionFactory,
    ResourceFactory,
    SuperUserFactory,
    UserFactory,
)
from testutils.permissions import add_permissions


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

    def test_returns_404_when_expense_has_no_image(self, client, db):
        """Test 404 when expense exists but has no image (user must have access)."""
        user = SuperUserFactory()
        client.login(username=user.username, password='password')
        expense = ExpenseFactory(image=None)
        url = reverse('media-auth:expense-image', args=[expense.pk])

        response = client.get(url)

        assert response.status_code == 404

    def test_returns_x_accel_redirect_for_valid_image(self, client, db):
        """Test valid access by superuser."""
        user = SuperUserFactory()
        client.login(username=user.username, password='password')

        filename = 'receipt.jpg'
        image = MagicMock(spec=File)
        image.name = filename
        expense = ExpenseFactory(image=image)

        url = reverse('media-auth:expense-image', args=[expense.pk])
        response = client.get(url)

        assert response.status_code == 200
        assert 'X-Accel-Redirect' in response
        assert response['X-Accel-Redirect'] == f'{settings.PRIVATE_MEDIA_URL}{expense.image.name}'
        assert response['Content-Disposition'] == f'inline; filename="{expense.image.name.split("/")[-1]}"'

    def test_superuser_can_access_any_expense(self, client, db):
        """Superuser should have access to any expense."""
        superuser = SuperUserFactory()
        client.login(username=superuser.username, password='password')

        filename = 'receipt.jpg'
        image = MagicMock(spec=File)
        image.name = filename
        expense = ExpenseFactory(image=image)

        url = reverse('media-auth:expense-image', args=[expense.pk])
        response = client.get(url)

        assert response.status_code == 200
        assert 'X-Accel-Redirect' in response

    def test_user_with_view_any_expense_permission_can_access(self, client, db):
        """User with view_any_expense permission should have access."""
        user = UserFactory()
        ResourceFactory(user=user)
        add_permissions(user, 'core.view_any_expense')
        client.login(username=user.username, password='password')

        filename = 'receipt.jpg'
        image = MagicMock(spec=File)
        image.name = filename
        expense = ExpenseFactory(image=image)

        url = reverse('media-auth:expense-image', args=[expense.pk])
        response = client.get(url)

        assert response.status_code == 200
        assert 'X-Accel-Redirect' in response

    def test_user_with_manage_any_expense_permission_can_access(self, client, db):
        """User with manage_any_expense permission should have access."""
        user = UserFactory()
        ResourceFactory(user=user)
        add_permissions(user, 'core.manage_any_expense')
        client.login(username=user.username, password='password')

        filename = 'receipt.jpg'
        image = MagicMock(spec=File)
        image.name = filename
        expense = ExpenseFactory(image=image)

        url = reverse('media-auth:expense-image', args=[expense.pk])
        response = client.get(url)

        assert response.status_code == 200
        assert 'X-Accel-Redirect' in response

    def test_user_with_same_resource_can_access_expense(self, client, db):
        """User whose resource matches the expense's mission resource can access."""
        user = UserFactory()
        resource = ResourceFactory(user=user)
        client.login(username=user.username, password='password')

        # Create expense with mission belonging to this resource
        mission = MissionFactory(resource=resource)
        filename = 'receipt.jpg'
        image = MagicMock(spec=File)
        image.name = filename
        expense = ExpenseFactory(mission=mission, image=image)

        url = reverse('media-auth:expense-image', args=[expense.pk])
        response = client.get(url)

        assert response.status_code == 200
        assert 'X-Accel-Redirect' in response

    def test_user_without_permission_gets_403(self, client, db):
        """User without permission should get 403 Forbidden."""
        user = UserFactory()
        ResourceFactory(user=user)  # User has a resource but not matching the expense
        client.login(username=user.username, password='password')

        # Create expense belonging to a different resource
        other_resource = ResourceFactory()
        mission = MissionFactory(resource=other_resource)
        filename = 'receipt.jpg'
        image = MagicMock(spec=File)
        image.name = filename
        expense = ExpenseFactory(mission=mission, image=image)

        url = reverse('media-auth:expense-image', args=[expense.pk])
        response = client.get(url)

        assert response.status_code == 403


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

    def test_returns_404_when_contract_has_no_document(self, client, db):
        """Test 404 when contract exists but has no document (user must have access)."""
        user = SuperUserFactory()
        client.login(username=user.username, password='password')
        contract = ContractFactory(document=None)
        url = reverse('media-auth:contract-document', args=[contract.pk])

        response = client.get(url)

        assert response.status_code == 404

    def test_returns_x_accel_redirect_for_valid_document(self, client, db):
        """Test valid access by superuser."""
        user = SuperUserFactory()
        client.login(username=user.username, password='password')

        filename = 'contract.pdf'
        # Create contract first (without document) so it gets an ID
        contract = ContractFactory(document=None)

        # Create mock and assign document after contract has an ID
        document = MagicMock(spec=File)
        document.name = filename
        contract.document = document
        contract.save()

        url = reverse('media-auth:contract-document', args=[contract.pk])
        response = client.get(url)

        assert response.status_code == 200
        assert 'X-Accel-Redirect' in response
        assert response['X-Accel-Redirect'] == f'{settings.PRIVATE_MEDIA_URL}{contract.document.name}'
        assert response['Content-Disposition'] == f'inline; filename="{contract.document.name.split("/")[-1]}"'

    def test_superuser_can_access_any_contract(self, client, db):
        """Superuser should have access to any contract."""
        superuser = SuperUserFactory()
        client.login(username=superuser.username, password='password')

        filename = 'contract.pdf'
        contract = ContractFactory(document=None)
        document = MagicMock(spec=File)
        document.name = filename
        contract.document = document
        contract.save()

        url = reverse('media-auth:contract-document', args=[contract.pk])
        response = client.get(url)

        assert response.status_code == 200
        assert 'X-Accel-Redirect' in response

    def test_user_with_view_any_contract_permission_can_access(self, client, db):
        """User with view_any_contract permission should have access."""
        user = UserFactory()
        ResourceFactory(user=user)
        add_permissions(user, 'core.view_any_contract')
        client.login(username=user.username, password='password')

        filename = 'contract.pdf'
        contract = ContractFactory(document=None)
        document = MagicMock(spec=File)
        document.name = filename
        contract.document = document
        contract.save()

        url = reverse('media-auth:contract-document', args=[contract.pk])
        response = client.get(url)

        assert response.status_code == 200
        assert 'X-Accel-Redirect' in response

    def test_user_with_manage_any_contract_permission_can_access(self, client, db):
        """User with manage_any_contract permission should have access."""
        user = UserFactory()
        ResourceFactory(user=user)
        add_permissions(user, 'core.manage_any_contract')
        client.login(username=user.username, password='password')

        filename = 'contract.pdf'
        contract = ContractFactory(document=None)
        document = MagicMock(spec=File)
        document.name = filename
        contract.document = document
        contract.save()

        url = reverse('media-auth:contract-document', args=[contract.pk])
        response = client.get(url)

        assert response.status_code == 200
        assert 'X-Accel-Redirect' in response

    def test_user_with_same_resource_can_access_contract(self, client, db):
        """User whose resource matches the contract's resource can access."""
        user = UserFactory()
        resource = ResourceFactory(user=user)
        client.login(username=user.username, password='password')

        filename = 'contract.pdf'
        contract = ContractFactory(resource=resource, document=None)
        document = MagicMock(spec=File)
        document.name = filename
        contract.document = document
        contract.save()

        url = reverse('media-auth:contract-document', args=[contract.pk])
        response = client.get(url)

        assert response.status_code == 200
        assert 'X-Accel-Redirect' in response

    def test_user_without_permission_gets_403(self, client, db):
        """User without permission should get 403 Forbidden."""
        user = UserFactory()
        ResourceFactory(user=user)  # User has a resource but not matching the contract
        client.login(username=user.username, password='password')

        # Create contract belonging to a different resource
        other_resource = ResourceFactory()
        filename = 'contract.pdf'
        contract = ContractFactory(resource=other_resource, document=None)
        document = MagicMock(spec=File)
        document.name = filename
        contract.document = document
        contract.save()

        url = reverse('media-auth:contract-document', args=[contract.pk])
        response = client.get(url)

        assert response.status_code == 403


class TestServeDocumentFile:
    """Tests for the serve_document_file view."""

    def test_unauthenticated_user_is_redirected_to_login(self, client, db):
        doc = DocumentFactory()
        url = reverse('media-auth:document-file', args=[doc.pk])

        response = client.get(url)

        assert response.status_code == 302
        assert '/login/' in response.url

    def test_returns_404_for_non_existent_document(self, resource_client, db):
        url = reverse('media-auth:document-file', args=[99999])

        response = resource_client.get(url)

        assert response.status_code == 404

    def test_returns_404_when_document_has_no_file(self, client, db):
        """Test 404 when document exists but has no file (user must have access as admin)."""
        user = UserFactory()
        client.login(username=user.username, password='password')
        doc = DocumentFactory(document=None, admin=user)
        url = reverse('media-auth:document-file', args=[doc.pk])

        response = client.get(url)

        assert response.status_code == 404

    def test_returns_x_accel_redirect_for_valid_file(self, client, db):
        """Test valid access by document admin."""
        user = UserFactory()
        client.login(username=user.username, password='password')

        doc = DocumentFactory(admin=user)

        url = reverse('media-auth:document-file', args=[doc.pk])
        response = client.get(url)

        assert response.status_code == 200
        assert 'X-Accel-Redirect' in response
        assert response['X-Accel-Redirect'] == f'{settings.PRIVATE_MEDIA_URL}{doc.document.name}'
        assert response['Content-Disposition'] == f'inline; filename="{doc.document.name.split("/")[-1]}"'

    def test_document_admin_can_access(self, client, db):
        """User who is admin of the document can access."""
        user = UserFactory()
        client.login(username=user.username, password='password')

        doc = DocumentFactory(admin=user)

        url = reverse('media-auth:document-file', args=[doc.pk])
        response = client.get(url)

        assert response.status_code == 200
        assert 'X-Accel-Redirect' in response

    def test_user_with_direct_grant_can_access(self, client, db):
        """User with a direct DocumentGrant can access."""
        user = UserFactory()
        client.login(username=user.username, password='password')

        doc = DocumentFactory()  # admin is someone else
        DocumentGrantFactory(user=user, document=doc, granted_permissions=['R'])

        url = reverse('media-auth:document-file', args=[doc.pk])
        response = client.get(url)

        assert response.status_code == 200
        assert 'X-Accel-Redirect' in response

    def test_user_with_group_grant_can_access(self, client, db):
        """User in a group with DocumentGrant can access."""
        user = UserFactory()
        group = GroupFactory()
        user.groups.add(group)
        client.login(username=user.username, password='password')

        doc = DocumentFactory()  # admin is someone else
        DocumentGrantFactory(user=None, group=group, document=doc, granted_permissions=['R'])

        url = reverse('media-auth:document-file', args=[doc.pk])
        response = client.get(url)

        assert response.status_code == 200
        assert 'X-Accel-Redirect' in response

    def test_user_without_permission_gets_403(self, client, db):
        """User without permission should get 403 Forbidden."""
        user = UserFactory()
        client.login(username=user.username, password='password')

        # Create document where user is NOT admin and has NO grant
        other_user = UserFactory()
        doc = DocumentFactory(admin=other_user)

        url = reverse('media-auth:document-file', args=[doc.pk])
        response = client.get(url)

        assert response.status_code == 403
