import re

import pytest

from krm3.missions.tables import ExpenseTableMixin


def solve_id(d: dict):
    if isinstance(d, dict):
        return {solve_id(k): solve_id(v) for k, v in d.items()}
    elif isinstance(d, list):
        return [solve_id(x) for x in d]
    elif hasattr(d, 'id'):
        return d.id
    elif isinstance(d, ExpenseTableMixin):
        z = [int(re.match(r'.*>(\d+)<.*', x.cells[0]).groups()[0]) for x in d.rows]
        return z


@pytest.fixture()
def scenario(categories, payment_types, document_types):
    from factories import ExpenseFactory, MissionFactory, ReimbursementFactory

    from krm3.missions.models import Expense, Mission, Reimbursement, Resource

    # Mission: m1 for resource res1
    #   Expenses:
    #     - m1e1
    #     - m1e2 (reimbursed with r1)
    #     - m1e3
    # Mission: m2 for resource res2
    #   Expenses:
    #     - m2e1
    # Mission: m3 for resource res1
    #   Expenses:
    #     - m3e1
    # Mission: m4 for resource res4 CANCELLED
    #   Expenses:
    #     - m4e1
    #     - m4e2

    m1e1: Expense = ExpenseFactory()
    m1: Mission = m1e1.mission
    res1: Resource = m1.resource
    r1: Reimbursement = ReimbursementFactory()
    m1e2 = ExpenseFactory(mission=m1, reimbursement=r1)  # skipped as already reimbursed
    m1e3 = ExpenseFactory(mission=m1)

    print(f'M1: <{m1.resource_id}: [{m1e1.pk}, {m1e3.pk}]>')

    m2: Mission = MissionFactory()
    res2: Resource = m2.resource
    m2e1: Expense = ExpenseFactory(mission=m2)
    print(f'<{m2.resource_id}: [{m2e1.pk}]>')

    m3: Mission = MissionFactory(resource=res1)  # same resource as m1
    m3e1: Expense = ExpenseFactory(mission=m3)

    m4: Mission = MissionFactory(status=Mission.MissionStatus.CANCELLED, resource=res2)
    m4e1 = ExpenseFactory(mission=m4)
    m4e2 = ExpenseFactory(mission=m4)

    ret = dict(
        res1=res1,
        res2=res2,
        m1=m1,
        m1e1=m1e1,
        m1e2=m1e2,
        m1e3=m1e3,
        r1=r1,
        m2=m2,
        m2e1=m2e1,
        m3=m3,
        m3e1=m3e1,
        m4=m4,
        m4e1=m4e1,
        m4e2=m4e2
    )
    return ret


def test_missions_reimbursement_action(scenario, resource, monkeypatch):
    from krm3.missions.admin import MissionAdmin
    from krm3.missions.models import Mission
    S = scenario

    to_reimburse, resources = MissionAdmin._reimburse(None, Mission.objects.all())

    assert solve_id(resources) == {
        S['res1'].id: {
            S['m1'].id: [S['m1e1'].id, S['m1e3'].id],
            S['m3'].id: [S['m3e1'].id]
        },
        S['res2'].id: {
            S['m2'].id: [S['m2e1'].id]
        }
    }
