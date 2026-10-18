"""Write access to missions and expenses of other resources requires the manage permission (#682)."""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from rest_framework.reverse import reverse
from testutils.factories import (
    DocumentTypeFactory,
    ExpenseCategoryFactory,
    ExpenseFactory,
    MissionFactory,
    PaymentCategoryFactory,
    ResourceFactory,
)

from krm3.core.models import Expense, Mission


def _user(regular_user, *codenames):
    regular_user.user_permissions.add(*Permission.objects.filter(codename__in=codenames))
    return get_user_model().objects.get(id=regular_user.id)  # invalidate the permission cache


def _own_resource(user):
    return ResourceFactory(user=user)


TARGETS = {
    'mission': {
        'model': Mission,
        'detail': 'missions-api:mission-detail',
        'view': 'view_any_mission',
        'manage': 'manage_any_mission',
        'make': lambda resource: MissionFactory(resource=resource, number=None, status='DRAFT'),
        'patch': {'title': 'changed'},
    },
    'expense': {
        'model': Expense,
        'detail': 'missions-api:expense-detail',
        'view': 'view_any_expense',
        'manage': 'manage_any_expense',
        'make': lambda resource: ExpenseFactory(mission=MissionFactory(resource=resource)),
        'patch': {'detail': 'changed'},
    },
}


@pytest.mark.parametrize('target', [pytest.param(k, id=k) for k in TARGETS])
@pytest.mark.parametrize(
    ('role', 'can_read', 'can_write'),
    [
        pytest.param('view-only', True, False, id='view-only'),
        pytest.param('manager', True, True, id='manager'),
        pytest.param('owner', True, True, id='owner'),
        pytest.param('unrelated', False, False, id='unrelated'),
    ],
)
def test_write_access(api_client, regular_user, target, role, can_read, can_write):
    cfg = TARGETS[target]
    perms = {'view-only': (cfg['view'],), 'manager': (cfg['manage'],)}.get(role, ())
    user = _user(regular_user, *perms)
    record = cfg['make'](_own_resource(user) if role == 'owner' else ResourceFactory())
    client = api_client(user=user)
    url = reverse(cfg['detail'], args=[record.pk])

    assert client.get(url).status_code == (200 if can_read else 404)

    response = client.patch(url, cfg['patch'], format='json')
    assert response.status_code == (200 if can_write else 403 if can_read else 404), response.data

    response = client.delete(url)
    assert response.status_code == (204 if can_write else 403 if can_read else 404)
    assert cfg['model'].objects.filter(pk=record.pk).exists() is not can_write


@pytest.mark.parametrize(
    ('perms', 'own_mission', 'expected'),
    [
        pytest.param((), True, 201, id='own-mission'),
        pytest.param(('view_any_expense',), False, 400, id='view-only-other-mission'),
        pytest.param(('manage_any_expense',), False, 201, id='manager-other-mission'),
    ],
)
def test_create_expense_on_mission(api_client, regular_user, perms, own_mission, expected):
    user = _user(regular_user, *perms)
    mission = MissionFactory(resource=_own_resource(user) if own_mission else ResourceFactory())
    payload = {
        'mission': mission.pk,
        'day': mission.from_date.isoformat(),
        'amountCurrency': '10.00',
        'currency': 'EUR',
        'category': ExpenseCategoryFactory().pk,
        'documentType': DocumentTypeFactory().pk,
        'paymentType': PaymentCategoryFactory().pk,
    }

    response = api_client(user=user).post(reverse('missions-api:expense-list'), payload, format='json')

    assert response.status_code == expected, response.data
    if expected == 400:
        assert 'mission' in response.data
    assert Expense.objects.filter(mission=mission).exists() == (expected == 201)


def test_owner_cannot_move_expense_to_other_mission(api_client, regular_user):
    user = _user(regular_user)
    expense = ExpenseFactory(mission=MissionFactory(resource=_own_resource(user)))
    other_mission = MissionFactory()

    response = api_client(user=user).patch(
        reverse('missions-api:expense-detail', args=[expense.pk]), {'mission': other_mission.pk}, format='json'
    )

    assert response.status_code == 400
    expense.refresh_from_db()
    assert expense.mission_id != other_mission.pk
