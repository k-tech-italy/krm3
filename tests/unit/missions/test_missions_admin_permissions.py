"""Missions admin honours the core.* mission/expense permissions for non-superusers (#686)."""

import pytest
from adminfilters.autocomplete import AutoCompleteFilter
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.urls import reverse
from testutils.factories import ResourceFactory, UserFactory

from krm3.core.models import Expense, Mission, Reimbursement

ROLES = {
    'plain': (),
    'mission-viewer': ('view_any_mission',),
    'mission-manager': ('manage_any_mission',),
    'expense-viewer': ('view_any_expense',),
    'expense-manager': ('manage_any_expense',),
}


def _staff(role, *extra):
    user = UserFactory(is_staff=True)
    user.user_permissions.add(*Permission.objects.filter(codename__in=ROLES[role] + extra))
    ResourceFactory(user=user)
    return get_user_model().objects.get(pk=user.pk)  # invalidate the permission cache


def _request(rf, user):
    request = rf.get('/')
    request.user = user
    return request


@pytest.mark.parametrize(
    ('model', 'resource_link', 'roles_with_filter'),
    [
        pytest.param(Mission, 'resource', {'mission-viewer', 'mission-manager'}, id='mission'),
        pytest.param(Reimbursement, 'resource', {'mission-viewer', 'mission-manager'}, id='reimbursement'),
        pytest.param(Expense, 'mission__resource', {'expense-viewer', 'expense-manager'}, id='expense'),
    ],
)
@pytest.mark.parametrize('role', [pytest.param(r, id=r) for r in ROLES])
def test_resource_filter(rf, db, model, resource_link, roles_with_filter, role):
    model_admin = admin.site._registry[model]

    filters = model_admin.get_list_filter(_request(rf, _staff(role)))

    assert ((resource_link, AutoCompleteFilter) in filters) == (role in roles_with_filter)


@pytest.mark.parametrize(
    ('role', 'prefilled'),
    [
        pytest.param('plain', True, id='plain'),
        pytest.param('mission-viewer', True, id='mission-viewer'),
        pytest.param('mission-manager', False, id='mission-manager'),
    ],
)
def test_add_mission_prefills_own_resource_only_for_non_managers(rf, db, role, prefilled):
    user = _staff(role)

    initial = admin.site._registry[Mission].get_changeform_initial_data(_request(rf, user))

    assert (initial.get('resource') == user.resource) is prefilled


@pytest.mark.parametrize(
    ('role', 'visible'),
    [
        pytest.param('plain', False, id='plain'),
        pytest.param('mission-viewer', False, id='mission-viewer'),
        pytest.param('mission-manager', True, id='mission-manager'),
    ],
)
def test_import_missions_button(client, db, role, visible):
    client.force_login(_staff(role, 'view_mission'))

    response = client.get(reverse('admin:core_mission_changelist'))

    assert response.status_code == 200
    assert ('import_missions' in response.content.decode()) is visible


@pytest.mark.parametrize(
    ('role', 'editable'),
    [
        pytest.param('plain', False, id='plain'),
        pytest.param('mission-viewer', True, id='mission-viewer'),
        pytest.param('mission-manager', True, id='mission-manager'),
    ],
)
def test_expense_reimbursement_field(rf, db, role, editable):
    readonly = admin.site._registry[Expense].get_readonly_fields(_request(rf, _staff(role)))

    assert ('reimbursement' not in readonly) is editable
