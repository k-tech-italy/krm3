import csv
import io

import pytest
from django.urls import reverse
from testutils.date_utils import _dt
from testutils.factories import ContractFactory, ProjectFactory, ResourceFactory, TaskEntryFactory, TaskFactory

MONTH = '202506'


def _read_csv(response) -> list[list[str]]:
    content = response.content.decode('utf-8')
    assert content.startswith('﻿'), 'The BOM tells spreadsheet applications the file is UTF-8'
    return list(csv.reader(io.StringIO(content.removeprefix('﻿'))))


def _rows_of(rows: list[list[str]], resource) -> list[list[str]]:
    name = f'{resource.last_name} {resource.first_name}'
    return [row for row in rows[1:] if row[0] == name]


@pytest.fixture
def report_data():
    """Two resources with contracts, each with a task on a different project in June 2025."""
    contract_1 = ContractFactory(period=(_dt('2020-01-01'), None))
    contract_2 = ContractFactory(period=(_dt('2020-01-01'), None))
    r1, r2 = contract_1.resource, contract_2.resource

    task_1 = TaskFactory(
        title='Analysis', project=ProjectFactory(name='Export project 1'), resource=r1, period=(_dt('2025-06-01'), None)
    )
    task_2 = TaskFactory(
        title='Development',
        project=ProjectFactory(name='Export project 2'),
        resource=r2,
        period=(_dt('2025-06-01'), None),
    )
    TaskEntryFactory(resource=r1, day=_dt('2025-06-16'), task=task_1, day_shift_hours=6, night_shift_hours=2)
    TaskEntryFactory(resource=r2, day=_dt('2025-06-17'), task=task_2, day_shift_hours=4)
    return {'r1': r1, 'r2': r2, 'task_1': task_1, 'task_2': task_2}


def test_export_returns_the_report_as_csv(admin_client, report_data):
    response = admin_client.get(reverse('export_task_report', args=[MONTH]))

    assert response.status_code == 200
    assert response['Content-Type'] == 'text/csv; charset=utf-8'
    assert response['Content-Disposition'] == 'attachment; filename="task_report_202506.csv"'

    rows = _read_csv(response)
    header = rows[0]
    assert header[:4] == ['Resource', 'Row', 'Days', 'Total HH']
    assert header[4] == '2025-06-01'
    assert header[-1] == '2025-06-30'
    assert len(header) == 4 + 30

    r1_rows = _rows_of(rows, report_data['r1'])
    assert r1_rows[0][1] == 'Scheduled'
    task_row = next(row for row in r1_rows if row[1] == str(report_data['task_1']))
    assert len(task_row) == len(header)
    assert task_row[header.index('2025-06-16')] == '8'
    assert task_row[3] == '8'
    assert any(row[1] == 'Absences' for row in r1_rows)
    assert _rows_of(rows, report_data['r2'])


@pytest.mark.parametrize(
    ('filters', 'included', 'excluded'),
    [
        pytest.param(lambda d: {'project': d['task_1'].project_id}, 'r1', 'r2', id='project'),
        pytest.param(lambda d: {'resource': d['r2'].pk}, 'r2', 'r1', id='resource'),
        pytest.param(lambda d: {'task': 'Development'}, 'r2', 'r1', id='task'),
    ],
)
def test_export_honors_the_filters(admin_client, report_data, filters, included, excluded):
    response = admin_client.get(reverse('export_task_report', args=[MONTH]), filters(report_data))

    rows = _read_csv(response)
    assert _rows_of(rows, report_data[included])
    assert not _rows_of(rows, report_data[excluded])


@pytest.mark.parametrize(
    ('query', 'has_absences'),
    [
        pytest.param({}, True, id='all-rows'),
        pytest.param({'tasks_only': '1'}, False, id='tasks-only'),
    ],
)
def test_export_honors_tasks_only(admin_client, report_data, query, has_absences):
    response = admin_client.get(reverse('export_task_report', args=[MONTH]), query)

    r1_rows = _rows_of(_read_csv(response), report_data['r1'])
    assert any(row[1] == 'Absences' for row in r1_rows) is has_absences


def test_export_marks_resources_without_tasks(admin_client, report_data):
    idle = ContractFactory(period=(_dt('2020-01-01'), None)).resource

    response = admin_client.get(reverse('export_task_report', args=[MONTH]))

    idle_rows = _rows_of(_read_csv(response), idle)
    assert [row[1] for row in idle_rows] == ['Scheduled', 'No tasks assigned']


def test_export_without_permission_contains_only_own_resource(resource_client, report_data):
    own = resource_client._resource
    ContractFactory(resource=own, period=(_dt('2020-01-01'), None))
    TaskFactory(title='Own task', resource=own, period=(_dt('2025-06-01'), None))

    # the filters are ignored for users who cannot see every resource
    response = resource_client.get(reverse('export_task_report', args=[MONTH]), {'resource': report_data['r1'].pk})

    rows = _read_csv(response)
    assert _rows_of(rows, own)
    assert not _rows_of(rows, report_data['r1'])
    assert not _rows_of(rows, report_data['r2'])


@pytest.mark.parametrize(
    ('query', 'expected_link'),
    [
        pytest.param('', f'/be/task_report/export/{MONTH}/"', id='no-filters'),
        pytest.param(
            '?resource=7&task=Analysis&tasks_only=1',
            f'/be/task_report/export/{MONTH}/?resource=7&amp;task=Analysis&amp;tasks_only=1"',
            id='filters',
        ),
    ],
)
def test_page_links_the_export_with_the_applied_filters(admin_client, query, expected_link):
    ResourceFactory()  # the filter values are passed through even when they match nothing

    response = admin_client.get(reverse('task-report-month', args=[MONTH]) + query)

    assert response.status_code == 200
    assert f'href="{expected_link}' in response.content.decode()
