"""Test invariants for mission model.

Note that no modifications are performed on the values of the fields.
Any modification is made in the form.

1. A DRAFT mission cannot have a number
"""
from contextlib import nullcontext as does_not_raise
from typing import TYPE_CHECKING

import pytest
from django.core.exceptions import ValidationError

from krm3.utils.dates import dt

if TYPE_CHECKING:
    from krm3.core.models import Mission


def map_mission_status(status: str) -> 'Mission.MissionStatus':
    from krm3.core.models import Mission
    return {
        'S': Mission.MissionStatus.SUBMITTED,
        'D': Mission.MissionStatus.DRAFT,
        'C': Mission.MissionStatus.CANCELLED
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
    ]
)
def test_mission_status_transitions(number, status, expectation):
    from testutils.factories import MissionFactory

    mission: Mission = MissionFactory.build(
        number=number, status=map_mission_status(status)
    )

    with expectation:
        mission.clean()
        assert True


@pytest.mark.parametrize(
    'from_date, to_date, expectation',  # noqa: PT007
    (
            pytest.param(dt('2023-11-03'), dt('2023-11-02'),
                         pytest.raises(ValidationError, match='to_date must be > from_date'),
                         id='prev-day'),
            pytest.param(dt('2023-12-01'), dt('2023-11-02'),
                         pytest.raises(ValidationError, match='to_date must be > from_date'),
                         id='prev-month'),
            pytest.param(dt('2023-11-02'), dt('2023-11-02'), does_not_raise(),
                         id='same-day'),
            pytest.param(dt('2023-10-20'), dt('2023-11-02'), does_not_raise(),
                         id='following-month'),
    )
)
def test_missions_validation(from_date, to_date, expectation):
    from testutils.factories import MissionFactory

    from krm3.core.models import Mission

    mission: Mission = MissionFactory.build(
        number=1, status=Mission.MissionStatus.SUBMITTED,
        from_date=from_date, to_date=to_date
    )

    with expectation:
        mission.clean()
        assert True


def test_calculate_number():
    from testutils.factories import MissionFactory

    from krm3.core.models import Mission

    assert Mission.calculate_number(None, 2023) == 1

    mission: Mission = MissionFactory(
        number=2, status=Mission.MissionStatus.SUBMITTED,
        from_date=dt('2023-11-03'), to_date=dt('2023-12-31')
    )

    assert Mission.calculate_number(None, 2023) == 1
    assert Mission.calculate_number(mission.id, 2023) == 1

    mission2 = MissionFactory(
        number=1, status=Mission.MissionStatus.SUBMITTED,
        from_date=dt('2023-11-03'), to_date=dt('2023-12-31')
    )

    assert Mission.calculate_number(None, 2023) == 3
    assert Mission.calculate_number(mission.id, 2023) == mission.number
    assert Mission.calculate_number(mission2.id, 2023) == mission2.number

    assert Mission.calculate_number(None, 2024) == 1
    mission.year = 2024
    mission.number = 1
    mission.save()

    assert Mission.calculate_number(None, 2024) == 2
