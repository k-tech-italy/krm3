from unittest.mock import Mock

import pytest
from django.contrib.messages import ERROR, get_messages
from django.urls import reverse
from testutils.factories import ExpenseFactory, MissionFactory, ReimbursementFactory

from krm3.currencies.models import Currency
from krm3.missions.admin import reimbursement as reimbursement_admin


@pytest.mark.parametrize(
    ('empty_count', 'valid_month'),
    [
        pytest.param(1, None, id='one-empty-reimbursement'),
        pytest.param(2, None, id='multiple-empty-reimbursements'),
        pytest.param(1, 'Apr', id='mixed-selection-same-month'),
        pytest.param(1, 'May', id='mixed-selection-different-months'),
    ],
)
def test_report_rejects_reimbursements_without_expenses(
    admin_client, categories, monkeypatch, empty_count, valid_month
):
    reimbursements = ReimbursementFactory.create_batch(empty_count, year=2025, month='Apr')
    if valid_month:
        reimbursement = ReimbursementFactory(year=2025, month=valid_month)
        eur = Currency.objects.get(pk='EUR')
        ExpenseFactory(
            mission=MissionFactory(default_currency=eur),
            currency=eur,
            amount_base=10,
            amount_reimbursement=10,
            reimbursement=reimbursement,
        )
        reimbursements.append(reimbursement)
    prepare_report = Mock(wraps=reimbursement_admin.prepare_reimbursement_report_context)
    monkeypatch.setattr(reimbursement_admin, 'prepare_reimbursement_report_context', prepare_report)
    url = reverse('admin:core_reimbursement_changelist')

    response = admin_client.post(
        url,
        {'action': 'report', '_selected_action': [reimbursement.pk for reimbursement in reimbursements]},
    )

    assert response.status_code == 302
    assert response.url == url
    prepare_report.assert_not_called()
    response = admin_client.get(response.url)
    assert response.status_code == 200
    messages = list(get_messages(response.wsgi_request))
    assert len(messages) == 1
    assert messages[0].level == ERROR
    assert str(messages[0]) == (
        'Cannot generate the reimbursement report because one or more selected reimbursements '
        'have no associated expenses.'
    )
    assert str(messages[0]) in response.content.decode()
