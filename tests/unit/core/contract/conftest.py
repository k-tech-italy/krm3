import datetime

import pytest

from krm3.core.models import Contract
from testutils.date_utils import _dt
from testutils.factories import ProjectFactory, ContractFactory, TaskFactory


@pytest.fixture
def contracts():
    c1: Contract = ContractFactory.create(period=(_dt('2020-01-01'), _dt('2020-07-01')))
    c2: Contract = ContractFactory.create(resource=c1.resource, period=(_dt('2020-07-01'), _dt('2021-01-01')))
    c3: Contract = ContractFactory.create(resource=c1.resource, period=(_dt('2021-01-01'), None))
    c4: Contract = ContractFactory.create(period=(_dt('2019-01-01'), _dt('2020-05-01')))
    c5: Contract = ContractFactory.create(resource=c4.resource, period=(_dt('2020-05-01'), _dt('2020-10-01')))

    return [c1, c2, c3, c4, c5]

@pytest.fixture
def contracts_and_tasks(contracts: list[Contract]):
    project = ProjectFactory()

    c1, c2, c3, c4, c5 = contracts

    return {
        'contracts': contracts,
        'tasks': [
            TaskFactory(
                resource=c1.resource,
                project=project,
                period=(_dt('2020-04-01'), _dt('2020-06-15')),
            ),
            TaskFactory(
                resource=c1.resource,
                project=project,
                period=(_dt('2020-06-01'), _dt('2020-08-31')),
            ),
            TaskFactory(
                resource=c1.resource,
                project=project,
                period=(_dt('2020-08-01'), None),
            ),
            TaskFactory(
                resource=c4.resource,
                project=project,
                period=(_dt('2020-01-01'), _dt('2020-03-15')),
            ),
        ],
    }
