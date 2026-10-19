"""Reimbursements can only be created through the Create reimbursement expense action (#685)."""

import datetime

import pytest
from django.contrib.auth.models import Permission
from django.urls import reverse
from testutils.factories import ReimbursementFactory, UserFactory

from krm3.core.models import Reimbursement


@pytest.fixture
def reimbursement_manager(db):
    user = UserFactory(is_staff=True)
    user.user_permissions.add(*Permission.objects.filter(content_type__model='reimbursement'))
    return user


@pytest.mark.parametrize('who', [pytest.param('superuser', id='superuser'), pytest.param('manager', id='manager')])
def test_add_reimbursement_is_forbidden(client, admin_user, reimbursement_manager, who):
    client.force_login(admin_user if who == 'superuser' else reimbursement_manager)

    assert client.get(reverse('admin:core_reimbursement_add')).status_code == 403
    response = client.post(reverse('admin:core_reimbursement_add'), {'year': 2025, 'month': 'Jan', 'title': ''})
    assert response.status_code == 403
    assert not Reimbursement.objects.exists()


def test_changelist_has_no_add_button(client, admin_user):
    client.force_login(admin_user)

    response = client.get(reverse('admin:core_reimbursement_changelist'))

    assert response.status_code == 200
    assert reverse('admin:core_reimbursement_add') not in response.content.decode()


def test_edit_keeps_number_and_sets_paid_date(client, admin_user):
    reimbursement = ReimbursementFactory(number=7, year=2025, month='Jan')
    client.force_login(admin_user)
    data = {
        'number': 7,
        'year': 2025,
        'month': 'Jan',
        'title': reimbursement.title,
        'resource': reimbursement.resource_id,
        'paid_date': '2025-02-10',
        'expenses-TOTAL_FORMS': 0,
        'expenses-INITIAL_FORMS': 0,
    }

    response = client.post(reverse('admin:core_reimbursement_change', args=[reimbursement.pk]), data)

    assert response.status_code == 302, response.context['adminform'].form.errors if response.context else ''
    reimbursement.refresh_from_db()
    assert (reimbursement.number, reimbursement.paid_date) == (7, datetime.date(2025, 2, 10))
