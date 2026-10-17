import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.urls import reverse
from testutils.factories import ExpenseFactory, ReimbursementFactory, UserFactory

from krm3.core.models import Reimbursement

REIMBURSE_URL = reverse('missions:reimburse-expenses')
RESULTS_URL = reverse('missions:reimburse-results')


def _user(*, staff: bool, perms: tuple[str, ...] = ()):
    user = UserFactory(is_staff=staff)
    user.user_permissions.add(*Permission.objects.filter(codename__in=perms))
    return get_user_model().objects.get(pk=user.pk)  # invalidate the permission cache


def _reimburse_payload():
    expense = ExpenseFactory()
    return {'expenses': str(expense.pk), 'year': expense.mission.year, 'month': 'Jan'}


@pytest.mark.parametrize(
    ('user_kwargs', 'expected'),
    [
        pytest.param(None, 302, id='anonymous'),
        pytest.param({'staff': False, 'perms': ('add_reimbursement',)}, 302, id='non-staff'),
        pytest.param({'staff': True}, 403, id='staff-without-permission'),
    ],
)
def test_reimburse_expenses_denied(client, user_kwargs, expected):
    payload = _reimburse_payload()
    if user_kwargs is not None:
        client.force_login(_user(**user_kwargs))

    response = client.post(REIMBURSE_URL, payload)

    assert response.status_code == expected
    if expected == 302:
        assert reverse('admin:login') in response.url
    assert not Reimbursement.objects.exists()


def test_reimburse_expenses_allowed(client):
    payload = _reimburse_payload()
    client.force_login(_user(staff=True, perms=('add_reimbursement',)))

    response = client.post(REIMBURSE_URL, payload)

    assert response.status_code == 302
    assert response.url.startswith(RESULTS_URL)
    assert Reimbursement.objects.count() == 1


@pytest.mark.parametrize(
    ('user_kwargs', 'expected'),
    [
        pytest.param(None, 302, id='anonymous'),
        pytest.param({'staff': False, 'perms': ('view_reimbursement',)}, 302, id='non-staff'),
        pytest.param({'staff': True}, 403, id='staff-without-permission'),
        pytest.param({'staff': True, 'perms': ('view_reimbursement',)}, 200, id='staff-with-permission'),
    ],
)
def test_reimburse_results_access(client, user_kwargs, expected):
    reimbursement = ReimbursementFactory()
    if user_kwargs is not None:
        client.force_login(_user(**user_kwargs))

    response = client.get(RESULTS_URL, {'ids': reimbursement.pk})

    assert response.status_code == expected
    if expected == 200:
        assert reimbursement.title in response.content.decode()
