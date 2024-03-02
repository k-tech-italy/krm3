import pytest
from django.shortcuts import reverse
from factory.fuzzy import FuzzyChoice


@pytest.fixture()
def scenario(categories, payment_types, document_types):
    from factories import ExpenseFactory, MissionFactory, ReimbursementFactory

    from krm3.missions.models import Expense, Mission, Reimbursement, Resource

    m1e1: Expense = ExpenseFactory()
    m1: Mission = m1e1.mission
    m1.status = Mission.MissionStatus.SUBMITTED
    m1.save()
    res1: Resource = m1.resource
    r1: Reimbursement = ReimbursementFactory()
    m1e2 = ExpenseFactory(mission=m1, reimbursement=r1)  # skipped as already reimbursed
    m1e3 = ExpenseFactory(mission=m1)
    print(f'<{m1.resource_id}: [{m1e1.pk}, {m1e3.pk}]>')

    m2: Mission = MissionFactory(status=Mission.MissionStatus.SUBMITTED)
    m2e1: Expense = ExpenseFactory()
    print(f'<{m2.resource_id}: [{m2e1.pk}]>')

    m3: Mission = MissionFactory()
    m3e1: Expense = ExpenseFactory(mission=m3)

    m1e2 = ExpenseFactory(mission=m1)
    m1e3 = ExpenseFactory(mission=m1, reimbursement=r1)

    ret = dict(
        m1e1=m1e1,
        m1=m1,
        res1=res1,
        r1=r1,
        m1e2=m1e2,
        m1e3=m1e3,
        m2=m2,
        m3=m3,
        m3e1=m3e1
    )
    return ret

#
# @pytest.parametrize(
#     'to_reimburse', [
#         pytest.param({}, id=''),
#     ]
# )
def test_missions_reimbursement_action(scenario, rf, resource, client, monkeypatch):
    from krm3.missions.admin import MissionAdmin
    from krm3.missions.models import Mission

    # monkeypatch.setattr("missions.reimbursement")
    request = rf.get(back := reverse('admin:missions_mission_changelist'))
    request.session = client.session
    ret = MissionAdmin.reimburse(None, request, Mission.objects.all())

    assert ret.status_code == 200
    assert request.session['back'] == back
    assert request.session['to-reimburse'] == {scenario['m1'].resource.id: [scenario['m1e1'].id, scenario['m1e3'].id]}
    # url = reverse('admin:missions')
    #
    # session = client.session
    # session['to-reimburse'] = {
    #     scenario['m1'].id : 1
    # }
    # session['back'] = 'dummy-back'
    #
    # url = reverse('missions:reimburse-mission')
    # response = client.post(url)
    # assert False
