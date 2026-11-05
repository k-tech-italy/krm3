from datetime import date

from django.urls import reverse
from testutils.factories import ContractFactory

from krm3.core.models import Contract

SCHEDULE = '{"mon": 4, "tue": 4, "wed": 4, "thu": 4, "fri": 4, "sat": 0, "sun": 0}'


def _change_url(contract: Contract) -> str:
    return reverse('admin:core_contract_change', args=[contract.pk])


def test_contract_change_form_saves_and_changes_the_version(krm3app, admin_user):
    contract = ContractFactory(period=(date(2026, 1, 1), None))
    version = contract.version
    form = krm3app.get(_change_url(contract), user=admin_user).forms['contract_form']
    form['working_schedule'] = SCHEDULE

    response = form.submit()

    assert response.status_code == 302
    contract.refresh_from_db()
    assert contract.working_schedule['mon'] == 4
    assert contract.version != version


def test_contract_change_form_rejects_a_stale_version(krm3app, admin_user):
    contract = ContractFactory(period=(date(2026, 1, 1), None))
    stale_form = krm3app.get(_change_url(contract), user=admin_user).forms['contract_form']
    first_form = krm3app.get(_change_url(contract), user=admin_user).forms['contract_form']
    first_form['working_schedule'] = SCHEDULE
    first_form.submit()
    stale_form['working_schedule'] = SCHEDULE.replace('4', '6')

    response = stale_form.submit()

    # the form is shown again with an error instead of failing with a server error
    assert response.status_code == 200
    assert 'Record Modified' in response.text
    contract.refresh_from_db()
    assert contract.working_schedule['mon'] == 4


def test_contract_changelist_renders(krm3app, admin_user):
    ContractFactory(period=(date(2026, 1, 1), None))

    response = krm3app.get(reverse('admin:core_contract_changelist'), user=admin_user)

    assert response.status_code == 200
