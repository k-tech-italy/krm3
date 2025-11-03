import random

import pytest

from testutils.date_utils import _dt
from testutils.factories import (
    ExpenseFactory,
    ReimbursementFactory,
    ResourceFactory,
    ProjectFactory,
    CityFactory,
)
from krm3.core.models import Reimbursement, Resource, Mission, PaymentCategory, ExpenseCategory
from krm3.currencies.models import Currency
from krm3.missions.admin.reimbursement import prepare_reimbursement_report_data, prepare_reimbursement_report_context

MARCH_EXPENSES = {
    '39,G': ['2025-03-01|2025-03-15', ['2025-03-12', '2025-03-29']],
    '40,G': ['2025-03-01|2025-03-31', ['2025-03-15']],
    '41,B': ['2025-03-01|2025-03-31', ['2025-03-21']],
    '42,B': ['2025-05-01|2025-05-31', ['2025-03-11']],
    '43,G': ['2025-03-01|2025-03-31', []],
    '45,G': ['2025-03-01|2025-03-31', []],
    '46,Z': ['2025-03-01|2025-03-31', []],
    '47,B': ['2025-04-01|2025-04-30', ['2025-03-10']],
}

MARCH_OUTCOME = {
    'G': ['^39', '40'],
    'B': ['41', '42*', '47*'],
}

APRIL_EXPENSES = {
    '40,G': ['2025-03-01|2025-03-31', ['2025-03-31']],
    '41,B': ['2025-03-01|2025-03-31', ['2025-04-11']],
    '42,B': ['2025-05-01|2025-05-31', ['2025-04-17']],
    '43,G': ['2025-03-01|2025-03-31', ['2025-03-31']],
    '47,B': ['2025-04-01|2025-04-30', ['2025-04-10']],
}

APRIL_OUTCOME = {
    'G': ['^40', '43'],
    'B': ['^41', '^42*', '^47'],
}

MAY_EXPENSES = {
    '41,B': ['2025-03-01|2025-03-31', ['2025-05-11']],
    '42,B': ['2025-05-01|2025-05-31', ['2025-05-27']],
    '44,B': ['2025-05-01|2025-05-31', ['2025-05-01']],
    '46,Z': ['2025-03-01|2025-03-31', ['2025-05-11']],
    '47,B': ['2025-04-01|2025-04-30', ['2025-05-20']],
}

MAY_OUTCOME = {
    'B': ['^41', '^42', '44', '^47'],
    'Z': ['^46'],
}


@pytest.fixture
def expenses(categories):
    return [
        [MARCH_EXPENSES, MARCH_OUTCOME],
        [APRIL_EXPENSES, APRIL_OUTCOME],
        [MAY_EXPENSES, MAY_OUTCOME],
    ]


def test_reimbursement_report_data_marker(expenses):
    resource_cache = {}
    mission_defaults = {
        'project': ProjectFactory(),
        'city': CityFactory(),
        'default_currency': Currency.objects.first(),
    }

    reimbursments_per_resource = {}
    for i, (expense_set, outcome) in enumerate(expenses):
        prepare_data(expense_set, i, reimbursments_per_resource, resource_cache, mission_defaults)

        result = prepare_reimbursement_report_data(
            Reimbursement.objects.filter(id__in=[r.id for r in reimbursments_per_resource[i].values()])
        )
        assert Resource.objects.count() == len(resource_cache)
        result = {resource.last_name: list(v.keys()) for resource, v in result.items()}
        assert result == outcome
    assert Mission.objects.count() == 47 - 39 + 1


def prepare_data(expense_set, i, reimbursments_per_resource, resource_cache, mission_defaults):
    for mission, expense_data in expense_set.items():
        m_number, r_surname = mission.split(',')
        m_from, m_to = expense_data[0].split('|')

        resource = resource_cache.get(r_surname)
        if not resource:
            resource = resource_cache[r_surname] = ResourceFactory(last_name=r_surname)

        mission_obj, _ = Mission.objects.get_or_create(
            year=2025,
            number=int(m_number),
            defaults={
                'resource': resource,
                'from_date': m_from,
                'to_date': m_to,
                'status': 'SUBMITTED',
                **mission_defaults,
            }
        )

        reimbursement = reimbursments_per_resource.setdefault(i, {}).setdefault(
            r_surname, ReimbursementFactory(resource=resource, year=2025, month=['Mar', 'Apr', 'May'][i])
        )

        expense_categories = list(ExpenseCategory.objects.all())
        payment_categories = list(PaymentCategory.objects.all())
        for day in expense_data[1]:
            payment_type = random.choice(payment_categories)
            ExpenseFactory(
                mission=mission_obj,
                day=_dt(day),
                reimbursement=reimbursement,
                category=random.choice(expense_categories),
                payment_type=payment_type,
            )


def test_reimbursement_report_context(expenses):
    resource_cache = {}
    mission_defaults = {
        'project': ProjectFactory(),
        'city': CityFactory(),
        'default_currency': Currency.objects.first(),
    }

    reimbursments_per_resource = {}
    for i, (expense_set, _) in enumerate(expenses):
        prepare_data(expense_set, i, reimbursments_per_resource, resource_cache, mission_defaults)

    context = prepare_reimbursement_report_context(Reimbursement.objects.all())
    assert list(context.keys()) == ['Mar 2025', 'Apr 2025', 'May 2025']
    missions = []
    for resources in context.values():
        first = next(iter(resources))
        missions.append(len(resources[first]))
    assert missions == [4, 4, 5]
