"""A mission's project must be one its resource is involved in today or later (via a task)."""

import pytest
from freezegun import freeze_time
from ktcalendars import KTDateRange
from rest_framework.reverse import reverse
from testutils.factories import (
    CityFactory,
    ContractFactory,
    MissionFactory,
    ProjectFactory,
    ResourceFactory,
    TaskFactory,
)

from krm3.core.models import Mission


@pytest.fixture
def involved_resource():
    resource = ResourceFactory()
    ContractFactory(resource=resource, period=KTDateRange('2026-01-01', None))
    return resource


def _payload(resource, project):
    return {
        'fromDate': '2026-09-10',
        'toDate': '2026-09-12',
        'project': project.id,
        'city': CityFactory().id,
        'resource': resource.id,
    }


@freeze_time('2026-09-07')
@pytest.mark.parametrize(
    ('task_period', 'expected'),
    [
        pytest.param(None, 400, id='no-task'),
        pytest.param(('2026-01-01', '2026-09-07'), 400, id='task-ended-yesterday'),
        pytest.param(('2026-01-01', '2026-09-08'), 201, id='task-ends-today'),
        pytest.param(('2026-10-01', None), 201, id='future-task'),
    ],
)
def test_create_requires_involvement(api_client, admin_user, involved_resource, task_period, expected):
    project = ProjectFactory(period=KTDateRange('2026-01-01', None))
    if task_period:
        TaskFactory(project=project, resource=involved_resource, period=KTDateRange(*task_period))

    response = api_client(user=admin_user).post(
        reverse('missions-api:mission-list'), _payload(involved_resource, project), format='json'
    )

    assert response.status_code == expected, response.data
    if expected == 400:
        assert 'project' in response.data
    assert Mission.objects.filter(project=project).exists() == (expected == 201)


@freeze_time('2026-09-07')
def test_create_rejects_project_of_another_resource(api_client, admin_user, involved_resource):
    task = TaskFactory(period=KTDateRange('2026-01-01', None), contract=True)

    response = api_client(user=admin_user).post(
        reverse('missions-api:mission-list'), _payload(involved_resource, task.project), format='json'
    )

    assert response.status_code == 400
    assert 'project' in response.data


@freeze_time('2026-09-07')
@pytest.mark.parametrize(
    ('patch', 'expected'),
    [
        pytest.param({'title': 'changed'}, 200, id='unchanged-project-not-rechecked'),
        pytest.param('new-project', 400, id='changed-to-uninvolved-project'),
    ],
)
def test_update(api_client, admin_user, involved_resource, patch, expected):
    # an existing mission whose project the resource is no longer involved in
    mission = MissionFactory(resource=involved_resource, number=None, status='DRAFT')
    if patch == 'new-project':
        patch = {'project': ProjectFactory(period=KTDateRange('2026-01-01', None)).id}

    response = api_client(user=admin_user).patch(
        reverse('missions-api:mission-detail', args=[mission.pk]), patch, format='json'
    )

    assert response.status_code == expected, response.data
