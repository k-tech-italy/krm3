"""The mission admin reports invalid input via messages instead of crashing (#690)."""

import datetime

import pytest
from django.contrib.messages import get_messages
from django.core.exceptions import ValidationError
from django.urls import reverse
from testutils.factories import CityFactory, ProjectFactory, ResourceFactory

from krm3.core.models import Mission
from krm3.missions.admin.mission import MissionAdmin

TODAY = datetime.date.today()


def _data(**overrides):
    data = {
        'from_date': TODAY.isoformat(),
        'to_date': TODAY.isoformat(),
        'project': ProjectFactory().pk,
        'city': CityFactory().pk,
        'resource': ResourceFactory().pk,
        'status': Mission.MissionStatus.DRAFT,
        'default_currency': 'EUR',
        'expenses-TOTAL_FORMS': 0,
        'expenses-INITIAL_FORMS': 0,
    }
    for key, value in overrides.items():
        if value is None:
            data.pop(key)
        else:
            data[key] = value
    return data


def _messages(response):
    return [str(m) for m in get_messages(response.wsgi_request)]


@pytest.mark.parametrize(
    ('overrides', 'expected_message'),
    [
        pytest.param(
            {'project': None, 'city': None, 'resource': None, 'status': None},
            'City: This field is required.',
            id='dates-only',
        ),
        pytest.param({'city': None}, 'City: This field is required.', id='draft-no-city'),
        pytest.param(
            {'city': None, 'status': Mission.MissionStatus.SUBMITTED},
            'City: This field is required.',
            id='submitted-no-city',
        ),
        pytest.param({'status': None}, 'Status: This field is required.', id='no-status'),
        pytest.param({'project': None}, 'Project: This field is required.', id='no-project'),
        pytest.param(
            {'to_date': (TODAY - datetime.timedelta(days=1)).isoformat()},
            'to_date must be > from_date',
            id='to-before-from',
        ),
    ],
)
def test_incomplete_mission_is_reported_with_messages(admin_client, overrides, expected_message):
    response = admin_client.post(reverse('admin:core_mission_add'), _data(**overrides))

    assert response.status_code == 200  # the form is shown again with the data entered
    assert expected_message in _messages(response)
    assert not Mission.objects.exists()


@pytest.mark.parametrize(
    'status',
    [
        pytest.param(Mission.MissionStatus.DRAFT, id='draft'),
        pytest.param(Mission.MissionStatus.SUBMITTED, id='submitted'),
        pytest.param(Mission.MissionStatus.CANCELLED, id='cancelled'),
    ],
)
def test_complete_mission_is_added(admin_client, status):
    response = admin_client.post(reverse('admin:core_mission_add'), _data(status=status))

    assert response.status_code == 302, _messages(response)
    mission = Mission.objects.get()
    assert mission.status == status
    assert (mission.number is None) == (status == Mission.MissionStatus.DRAFT)


def test_error_while_saving_becomes_a_message(admin_client, monkeypatch):
    def failing_save_model(*args, **kwargs):  # noqa: ANN002, ANN003, ANN202
        raise ValidationError('something went wrong')

    monkeypatch.setattr(MissionAdmin, 'save_model', failing_save_model)
    url = reverse('admin:core_mission_add')

    response = admin_client.post(url, _data())

    assert response.status_code == 302
    assert response.url == url
    assert 'something went wrong' in _messages(response)
    assert not Mission.objects.exists()


@pytest.mark.parametrize(
    ('data', 'expected'),
    [
        pytest.param({'from_date': TODAY, 'to_date': TODAY}, '', id='no-city-no-resource'),
        pytest.param({'from_date': TODAY, 'to_date': TODAY, 'number': 3, 'year': 2026}, '', id='no-city'),
    ],
)
def test_calculate_title_with_incomplete_data(db, data, expected):
    assert Mission.calculate_title(data) == expected
