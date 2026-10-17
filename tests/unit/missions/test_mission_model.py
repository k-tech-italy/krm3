"""Test invariants for mission model.

Note that no modifications are performed on the values of the fields.
Any modification is made in the form.

1. A DRAFT mission cannot have a number
"""

from contextlib import nullcontext as does_not_raise

import pytest
from django.core.exceptions import ValidationError
from testutils.date_utils import _dt
from testutils.factories import MissionFactory

from krm3.core.models import Mission


def map_mission_status(status: str) -> 'Mission.MissionStatus':
    return {
        'S': Mission.MissionStatus.SUBMITTED,
        'D': Mission.MissionStatus.DRAFT,
        'C': Mission.MissionStatus.CANCELLED,
    }[status]


@pytest.mark.parametrize(
    'number, status, expectation',
    [
        pytest.param(None, 'C', pytest.raises(ValidationError), id='cancelled-none'),
        pytest.param(1, 'C', does_not_raise(), id='cancelled-num'),
        pytest.param(None, 'D', does_not_raise(), id='draft-none'),
        pytest.param(1, 'D', pytest.raises(ValidationError), id='draft-none'),
        pytest.param(None, 'S', pytest.raises(ValidationError), id='submitted'),
        pytest.param(1, 'S', does_not_raise(), id='submitted'),
    ],
)
def test_mission_status_transitions(number, status, expectation):
    mission: Mission = MissionFactory.build(number=number, status=map_mission_status(status))

    with expectation:
        mission.clean()
        assert True


@pytest.mark.parametrize(
    'from_date, to_date, expectation',  # noqa: PT007
    (
        pytest.param(
            _dt('2023-11-03'),
            _dt('2023-11-02'),
            pytest.raises(ValidationError, match='to_date must be > from_date'),
            id='prev-day',
        ),
        pytest.param(
            _dt('2023-12-01'),
            _dt('2023-11-02'),
            pytest.raises(ValidationError, match='to_date must be > from_date'),
            id='prev-month',
        ),
        pytest.param(_dt('2023-11-02'), _dt('2023-11-02'), does_not_raise(), id='same-day'),
        pytest.param(_dt('2023-10-20'), _dt('2023-11-02'), does_not_raise(), id='following-month'),
    ),
)
def test_missions_validation(from_date, to_date, expectation):
    mission: Mission = MissionFactory.build(
        number=1, status=Mission.MissionStatus.SUBMITTED, from_date=from_date, to_date=to_date
    )

    with expectation:
        mission.clean()
        assert True


def test_calculate_number():
    assert Mission.calculate_number(None, 2023) == 1

    mission: Mission = MissionFactory(
        number=2, status=Mission.MissionStatus.SUBMITTED, from_date=_dt('2023-11-03'), to_date=_dt('2023-12-31')
    )

    assert Mission.calculate_number(None, 2023) == 1
    assert Mission.calculate_number(mission.id, 2023) == 1

    mission2 = MissionFactory(
        number=1, status=Mission.MissionStatus.SUBMITTED, from_date=_dt('2023-11-03'), to_date=_dt('2023-12-31')
    )

    assert Mission.calculate_number(None, 2023) == 3
    assert Mission.calculate_number(mission.id, 2023) == mission.number
    assert Mission.calculate_number(mission2.id, 2023) == mission2.number

    assert Mission.calculate_number(None, 2024) == 1
    mission.year = 2024
    mission.number = 1
    mission.save()

    assert Mission.calculate_number(None, 2024) == 2


def test_year_defaults_to_from_date_year():
    mission: Mission = MissionFactory.build(
        number=None, year=None, status=Mission.MissionStatus.DRAFT, from_date=_dt('2023-12-30')
    )
    mission.clean()
    assert mission.year == 2023


def test_submit_assigns_number_restarting_every_year():
    for number in (1, 2):
        MissionFactory(number=number, status=Mission.MissionStatus.SUBMITTED, from_date=_dt('2023-03-01'))

    draft_2023 = MissionFactory(number=None, year=None, status=Mission.MissionStatus.DRAFT, from_date=_dt('2023-06-01'))
    draft_2024 = MissionFactory(number=None, year=None, status=Mission.MissionStatus.DRAFT, from_date=_dt('2024-01-02'))
    assert draft_2023.number is None
    assert draft_2024.number is None

    draft_2023.submit()
    draft_2024.submit()
    draft_2023.refresh_from_db()
    draft_2024.refresh_from_db()

    assert (draft_2023.status, draft_2023.year, draft_2023.number) == (Mission.MissionStatus.SUBMITTED, 2023, 3)
    assert (draft_2024.status, draft_2024.year, draft_2024.number) == (Mission.MissionStatus.SUBMITTED, 2024, 1)


def test_submit_keeps_number_if_already_set():
    mission = MissionFactory(number=None, status=Mission.MissionStatus.DRAFT, from_date=_dt('2023-06-01'))
    mission.number = 7
    mission.submit()
    mission.refresh_from_db()
    assert mission.number == 7


@pytest.mark.parametrize(
    'status',
    [
        pytest.param(Mission.MissionStatus.SUBMITTED, id='submitted'),
        pytest.param(Mission.MissionStatus.CANCELLED, id='cancelled'),
    ],
)
def test_submit_rejects_non_draft(status):
    mission = MissionFactory(number=1, status=status)
    with pytest.raises(ValidationError, match='Cannot change status'):
        mission.submit()
