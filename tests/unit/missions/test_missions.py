from contextlib import nullcontext as does_not_raise

import pytest
from django.core.exceptions import ValidationError

# from krm3.missions.models import Mission


@pytest.mark.parametrize(
    'from_date, to_date, expectation',
    (
            pytest.param('2023-11-03', '2023-11-02',
                         pytest.raises(ValidationError, match='to_date must be > from_date'),
                         id='prev-day'),
            pytest.param('2023-12-01', '2023-11-02',
                         pytest.raises(ValidationError, match='to_date must be > from_date'),
                         id='prev-month'),
            pytest.param('2023-11-02', '2023-11-02', does_not_raise(),
                         id='same-day'),
            pytest.param('2023-10-20', '2023-11-02', does_not_raise(),
                         id='following-month'),
    )
)
def test_missions_validation(from_date, to_date, expectation, mission):
    mission.from_date = from_date
    mission.to_date = to_date
    with expectation:
        mission.save()

    print(1)
    # missions = Mission.objects.all()
    # assert missions.count() == 0
    # 1. creare un esempio
    # 2. provae a salvare
    # 3. valutare risultato
    # assert False
