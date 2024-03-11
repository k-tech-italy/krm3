import pytest
from django.shortcuts import reverse
from testutils import map_mission_status

from krm3.missions.forms import MissionAdminForm
from krm3.utils.dates import dt


@pytest.mark.parametrize(
    'input, expected',
    [
        pytest.param([], 1, id='empty'),
        pytest.param([1], 2, id='one'),
        pytest.param([1, 3, 2], 4, id='sequence'),
        pytest.param([1, 3, '-2'], 4, id='gap-cancelled'),
        pytest.param(['-1', '-2', '-3'], 4, id='all-cancelled'),
        pytest.param([1, 3], 2, id='gap'),
        pytest.param([9, 2, 1], 3, id='big-gap'),
        pytest.param([4, '-2', 1], 3, id='cancelled-gap'),
    ]
)
def test_calculate_mission_number(input, expected):
    from factories import MissionFactory

    from krm3.missions.models import Mission
    for m in input:
        MissionFactory(
            number=abs(int(m)),
            status=Mission.MissionStatus.SUBMITTED if isinstance(m, int) else Mission.MissionStatus.CANCELLED,
            year=2020
        )
    form = MissionAdminForm()
    form.cleaned_data = {'year': 2020}
    outcome = form.calculate_number()
    assert outcome == expected


@pytest.mark.parametrize(
    'existing_status, this_status, expected_number, same_year',
    [
        pytest.param('D', 'S', 1, True, id='first-submitted'),
        pytest.param(None, 'S', 1, True, id='only-submitted'),
        pytest.param(1, 'S', 2, True, id='all-submitted-same-year'),
        pytest.param(4, 'S', 1, True, id='all-submitted-gap'),
        pytest.param(1, 'S', 1, False, id='all-submitted-diff-year'),
        pytest.param('D', 'D', None, True, id='all-draft'),
        pytest.param(None, 'D', None, True, id='only-draft'),
    ]
)
def test_auto_mission_number(existing_status, this_status, expected_number, same_year, city, project, resource):
    from factories import MissionFactory

    from krm3.missions.models import Mission

    assert Mission.objects.count() == 0
    mission = None
    if existing_status and existing_status != 'D':
        mission = MissionFactory(status=Mission.MissionStatus.SUBMITTED, number=existing_status)
    elif existing_status:
        mission = MissionFactory(number=None, status=map_mission_status(existing_status))
    base = {
        'project': project,
        'city': city,
        'resource': resource,
        'from_date': mission.from_date if mission and same_year else dt('2000-01-01'),
        'to_date': mission.from_date if mission and same_year else dt('2000-01-01'),
        'status': map_mission_status(this_status),
    }
    form = MissionAdminForm(base)
    valid = form.is_valid()
    assert valid, f'Form should be valid. Instead {form.errors}'
    if expected_number:
        assert form.cleaned_data['number'] == expected_number, f'Should have assigned number {expected_number}'
    else:
        assert form.cleaned_data['number'] is None


@pytest.mark.parametrize(
    'prev, next, next_number, expected_number, reimbursed_expenses, err_msg',
    [
        pytest.param('D', 'S', 1, 1, None, None, id='first-submitted'),
        pytest.param('S', 'D', None, None, False, None, id='no-reimbursed-expenses'),
        pytest.param('S', 'D', 1, None, False, None, id='draft-number-not-none'),
        pytest.param('S', 'C', 1, 1, False, None, id='cancelled-number-not-none'),
        pytest.param(
            'S', 'D', None, None, True,
            'You cannot set to DRAFT a mission with reimbursed exception',
            id='draft-with-reimbursed-expenses'),
        pytest.param(
            'S', 'C', None, None, True,
            'You cannot set to CANCELLED a mission with reimbursed exception',
            id='cancelled-with-reimbursed-expenses'),
    ]
)
def test_mission_status_transitions(
        prev, next, next_number, expected_number, reimbursed_expenses, err_msg, krm3app, admin_user):
    from factories import ExpenseFactory, MissionFactory, ReimbursementFactory

    mission = MissionFactory(number=None if prev == 'D' else 1, status=map_mission_status(prev))
    if reimbursed_expenses is not None:
        if reimbursed_expenses:
            reimbursement = ReimbursementFactory()
            ExpenseFactory(mission=mission, reimbursement=reimbursement)
        else:
            ExpenseFactory(mission=mission, reimbursement=None)

    url = reverse('admin:missions_mission_change', args=[mission.id])
    form = krm3app.get(url, user=admin_user).forms['mission_form']
    form['status'] = map_mission_status(next)
    form['number'] = next_number
    response = form.submit()
    if response.status_code == 302:
        response = response.follow()
    assert response.status_code == 200
    if err_msg:
        assert f'<ul class="errorlist nonfield"><li>{err_msg}</li></ul>' in response.text
    else:
        mission.refresh_from_db()
        assert mission.number == expected_number
