from unittest.mock import MagicMock, Mock

import pytest
import responses
from django.core.files import File
from factories import ExpenseFactory, MissionFactory, PaymentCategoryFactory


@pytest.fixture
def mocked_messages(monkeypatch):
    monkeypatch.setattr('django.contrib.messages.api.add_message', mock := Mock())
    return mock


@responses.activate
@pytest.mark.parametrize(
    'expenses, counters', [
        pytest.param([
            ['P', 100, True],  # 100
            ['P', 102, True],  # 102
            ['P', 11, False],  # 0
            ['A', 80, True],  # 0
            ['A', 60, False],  # -60
            ['A', 21, False],  # 21
            ['A', 7, False],  # -7
        ], [2, 1, 1, 3], id='pers-wimage'),
    ]
)
def test_create_reimbursement(expenses, counters, mocked_messages, db, monkeypatch):
    monkeypatch.setattr('krm3.missions.actions.get_rates', Mock(return_value='Mocked get_rates'))

    from krm3.missions.actions import create_reimbursement
    from krm3.missions.models import Expense, Reimbursement

    assert Expense.objects.count() == 0

    expense_list = []
    for expense_type, amt_base, image in expenses:
        if image:
            image = MagicMock(spec=File)
            image.name = 'image.pdf'
        else:
            image = None

        payment_type = PaymentCategoryFactory(personal_expense=expense_type == 'P')
        mission = MissionFactory(status='SUBMITTED')
        expense_list.append(ExpenseFactory(amount_base=amt_base, image=image, payment_type=payment_type,
                                           reimbursement=None, mission=mission))

    create_reimbursement(modeladmin=None, request=None, expenses=Expense.objects.all())

    reimbursement = Reimbursement.objects.first()
    assert reimbursement.id

    messages = mocked_messages.call_args_list[0].args
    assert messages[2] == f'Mocked get_rates Assigned {len(expenses)} to new reimbursement' + \
           f" <a href=\"/admin/missions/reimbursement/{reimbursement.id}/change/\">{reimbursement}</a>." + \
           f' pers. con imm.={counters[0]},  pers. senza imm.={counters[1]},' + \
           f'  az. con imm.={counters[2]},  az. senza imm.={counters[3]}'
    assert messages[1] == 25  # django.contrib.messages.constants.SUCCESS
