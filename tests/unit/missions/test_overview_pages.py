"""Rendering of the mission / reimbursement overview and report admin pages (#691).

These pages broke twice unnoticed (update_rates() receiving a list, and the django-tables2 3.0
rename of its ``querystring`` tag), so they are rendered end to end here.
"""

import pytest
from django.urls import reverse
from testutils.factories import ExpenseFactory, MissionFactory, ReimbursementFactory

from krm3.currencies.models import Currency

XLSX = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'


@pytest.fixture
def eur(db):
    return Currency.objects.get(pk='EUR')


@pytest.fixture
def reimbursement(eur, categories):
    """A reimbursement with one EUR expense (the report needs the standard categories, e.g. Forfait)."""
    reimbursement = ReimbursementFactory()
    ExpenseFactory(
        mission=MissionFactory(default_currency=eur),
        currency=eur,
        amount_base=10,
        amount_reimbursement=10,
        reimbursement=reimbursement,
    )
    return reimbursement


@pytest.mark.parametrize('with_expense', [pytest.param(False, id='no-expenses'), pytest.param(True, id='with-expense')])
def test_mission_overview(admin_client, eur, with_expense):
    mission = MissionFactory(default_currency=eur)
    if with_expense:
        ExpenseFactory(mission=mission, currency=eur, amount_base=10)

    response = admin_client.get(reverse('admin:core_mission_overview', args=[mission.pk]))

    assert response.status_code == 200
    assert '_export=xlsx' in response.content.decode()


def test_mission_overview_xlsx_export(admin_client, eur):
    mission = MissionFactory(default_currency=eur)
    ExpenseFactory(mission=mission, currency=eur, amount_base=10)

    response = admin_client.get(reverse('admin:core_mission_overview', args=[mission.pk]), {'_export': 'xlsx'})

    assert response.status_code == 200
    assert response['Content-Type'] == XLSX


def test_reimbursement_overview(admin_client, reimbursement):
    response = admin_client.get(reverse('admin:core_reimbursement_overview', args=[reimbursement.pk]))

    assert response.status_code == 200
    assert '_export=xlsx' in response.content.decode()


def test_reimbursement_overview_xlsx_export(admin_client, reimbursement):
    response = admin_client.get(
        reverse('admin:core_reimbursement_overview', args=[reimbursement.pk]), {'_export': 'xlsx'}
    )

    assert response.status_code == 200
    assert response['Content-Type'] == XLSX


def test_reimbursement_report_action(admin_client, reimbursement):
    response = admin_client.post(
        reverse('admin:core_reimbursement_changelist'),
        {'action': 'report', '_selected_action': [reimbursement.pk]},
    )

    assert response.status_code == 200
    assert 'Reimbursements report' in response.content.decode()
