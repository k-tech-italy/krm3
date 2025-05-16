from decimal import Decimal

import pytest

from testutils.factories import ExpenseFactory
from krm3.core.models import Expense
from krm3.missions.utilities import calculate_reimbursement_summaries, ReimbursementSummaryEnum


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
                    'Forfait': '0.0,0.0',
                    'Rappresentanza': '0.0,0.0',
                    'Viaggio': '0.0,0.0',
                    'Vitto': '0.0,0.0',
                },
                'bypayment': {'Company': '0.0,0.0', 'Personal': '3.50,3.50'},
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
                    'Forfait': '0.0,0.0',
                    'Rappresentanza': '0.0,0.0',
                    'Viaggio': '0.0,0.0',
                    'Vitto': '0.0,0.0',
                },
                'bypayment': {'Company': '0.0,0.0', 'Personal': '3.50,1.60'},
            }
        case 'mixed':
            for category, payment_type, currency, base, reimbursement in [
                ['rappresentanza', 'personal', 1.1, 1.1, 1.1],
                ['rappresentanza', 'personal', 2.0, 2.4, 0.5],
                ['alloggio', 'personal', 1.1, 1.1, 1.1],
                ['alloggio', 'company', 10, 10.1, -5.4],
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
                    'Alloggio': '13.60,-3.80',
                    'Forfait': '3.50,0.50',
                    'Rappresentanza': '3.50,1.60',
                    'Viaggio': '1.30,0.0',
                    'Vitto': '2.40,0.0',
                },
                'bypayment': {'Company': '14.90,5.40', 'Personal': '9.40,3.70'},
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
    bypayment = {k: f'{v[0]},{v[1]}' for k, v in bypayment.items()}
    assert byexpcategory == dataset['byexpcategory']
    assert bypayment == dataset['bypayment']


@pytest.fixture
def expenses_for_crs(categories):
    ExpenseFactory(
        category=categories.expenses['forfait.vitto'],
        payment_type=categories.payments['personal'],
        amount_currency=0,
        amount_base=3010,
        amount_reimbursement=10,
    )
    ExpenseFactory(
        category=categories.expenses['forfait.vitto'],
        payment_type=categories.payments['company'],
        amount_currency=0,
        amount_base=5100,
        #  ATTENTION: reimbursement to company are entered as negative values
        # e.g. if the resourse needs to return 1000 it will be entered as -1000
        amount_reimbursement=-1000,
    )


@pytest.mark.parametrize(
    'key,outcome',
    [
        pytest.param(ReimbursementSummaryEnum.TOTALE_COSTO, 10 + 5100 - 1000, id='costo-azienda'),
        pytest.param(ReimbursementSummaryEnum.TOTALE_RIMBORSO, 10 - 1000, id='reimbursment'),
        pytest.param(ReimbursementSummaryEnum.NON_RIMBORSATE, 3010 - 10, id='non-reimbursed'),
        pytest.param(ReimbursementSummaryEnum.DA_RESTITUIRE, 1000, id='to-return'),
    ],
)
def test_crs_costo_azienda(key: ReimbursementSummaryEnum, outcome: int, expenses_for_crs):
    byexpcategory, bypayment, summary = calculate_reimbursement_summaries(Expense.objects.all())
    summary = {str(k): v for k, v in summary.items()}
    byexpcategory = {str(k): v for k, v in byexpcategory.items()}
    bypayment = {str(k): v for k, v in bypayment.items()}

    assert len(summary) == 5
    assert summary[key.value] == Decimal(outcome)
    assert summary['Forfait'] == Decimal(10 + 5100 - 1000)

    assert byexpcategory.pop('Forfait') == [
        Decimal(3010 + 5100),
        Decimal(10 - 1000),
        Decimal(3010 - 10 + 1000),
        Decimal(10 + 5100 - 1000),
    ]
    assert byexpcategory.pop('Alloggio') == [Decimal(0), Decimal(0), Decimal(0), Decimal(0)]
    assert byexpcategory.pop('Viaggio') == [Decimal(0), Decimal(0), Decimal(0), Decimal(0)]
    assert byexpcategory.pop('Rappresentanza') == [Decimal(0), Decimal(0), Decimal(0), Decimal(0)]
    assert byexpcategory.pop('Vitto') == [Decimal(0), Decimal(0), Decimal(0), Decimal(0)]
    assert len(byexpcategory) == 0

    assert bypayment == {
        'Company': [Decimal(5100), Decimal(1000), Decimal(5100 - 1000)],
        'Personal': [Decimal(3010), Decimal(10), Decimal(3010 - 10)],
    }
