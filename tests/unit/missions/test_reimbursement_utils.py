import pytest

from testutils.factories import ExpenseFactory
from krm3.core.models import Expense
from krm3.missions.utilities import calculate_reimbursement_summaries


@pytest.fixture
def dataset(request, categories):
    match request.getfixturevalue('scenario'):
        case 'all_personal':
            for category, payment_type, currency, base, reimbursement in [
                ['alloggio', 'personal', 1.1, 1.1, 1.1],
                ['alloggio', 'personal', 2.0, 2.4, 2.4],
            ]:
                ExpenseFactory(
                    category=categories.expenses[category],
                    payment_type=categories.payments[payment_type],
                    amount_currency=currency,
                    amount_base=base,
                    amount_reimbursement=reimbursement,
                )
            return {
                'byexpcategory': {
                    'Alloggio': '3.50,3.50',
                    'Forfait': '0,0',
                    'Rappresentanza': '0,0',
                    'Viaggio': '0,0',
                    'Vitto': '0,0',
                },
                'bypayment': {'Company': '0,0', 'Personal': '3.50,3.50'},
            }
        case 'partial_personal':
            for category, payment_type, currency, base, reimbursement in [
                ['alloggio', 'personal', 1.1, 1.1, 1.1],
                ['alloggio', 'personal', 2.0, 2.4, 0.5],
            ]:
                ExpenseFactory(
                    category=categories.expenses[category],
                    payment_type=categories.payments[payment_type],
                    amount_currency=currency,
                    amount_base=base,
                    amount_reimbursement=reimbursement,
                )
            return {
                'byexpcategory': {
                    'Alloggio': '3.50,1.60',
                    'Forfait': '0,0',
                    'Rappresentanza': '0,0',
                    'Viaggio': '0,0',
                    'Vitto': '0,0',
                },
                'bypayment': {'Company': '0,0', 'Personal': '3.50,1.60'},
            }
        case 'mixed':
            for category, payment_type, currency, base, reimbursement in [
                ['rappresentanza', 'personal', 1.1, 1.1, 1.1],
                ['rappresentanza', 'personal', 2.0, 2.4, 0.5],
                ['alloggio', 'personal', 1.1, 1.1, 1.1],
                ['alloggio', 'personal', 2.0, 2.4, 0.5],
                ['vitto', 'company', 2.0, 2.4, 0],
                ['forfait.alloggio', 'company.wire', 1.1, 1.1, 0],
                ['forfait.treno', 'personal', 2.0, 2.4, 0.5],
                ['viaggio', 'company.cca', 1.1, 1.3, 0],
            ]:
                ExpenseFactory(
                    category=categories.expenses[category],
                    payment_type=categories.payments[payment_type],
                    amount_currency=currency,
                    amount_base=base,
                    amount_reimbursement=reimbursement,
                )
            return {
                'byexpcategory': {
                    'Alloggio': '3.50,1.60',
                    'Forfait': '3.50,0.50',
                    'Rappresentanza': '3.50,1.60',
                    'Viaggio': '1.30,0',
                    'Vitto': '2.40,0',
                },
                'bypayment': {'Company': '4.80,0', 'Personal': '9.40,3.70'},
            }
        case _:
            raise ValueError(f'Unknown scenario {request.getfixturevalue("scenario")}')


@pytest.mark.parametrize(
    'scenario',
    [
        pytest.param('all_personal', id='all-personal'),
        pytest.param('partial_personal', id='partial-personal'),
        pytest.param('mixed', id='mixed'),
    ],
)
def test_calculate_reimbursement_summaries(dataset, scenario):
    byexpcategory, bypayment, summary = calculate_reimbursement_summaries(Expense.objects.all())
    byexpcategory = {k.title: f'{v[0]},{v[1]}' for k, v in byexpcategory.items()}
    bypayment = {k.title: f'{v[0]},{v[1]}' for k, v in bypayment.items()}
    assert byexpcategory == dataset['byexpcategory']
    assert bypayment == dataset['bypayment']
