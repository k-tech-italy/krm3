import io

import openpyxl
import pytest
from django.urls import reverse
from testutils.date_utils import _dt
from testutils.factories import ContractFactory, ProjectFactory, ResourceFactory, TaskEntryFactory, TaskFactory

from krm3.web.report_styles import nwd_fill

MONTH = '202506'


def _read_sheet(response) -> openpyxl.worksheet.worksheet.Worksheet:
    assert response.status_code == 200
    return openpyxl.load_workbook(io.BytesIO(response.content)).active


def _blocks(ws) -> dict[str, list[tuple]]:
    """Group the sheet rows by resource: each block starts with a header row and ends with an empty row."""
    blocks: dict[str, list[tuple]] = {}
    current = None
    for row in ws.iter_rows(values_only=True):
        if all(value is None for value in row):
            current = None
        elif current is None:
            current = blocks.setdefault(row[0], [])
            current.append(row)
        else:
            current.append(row)
    return blocks


def _name(resource) -> str:
    return f'{resource.last_name} {resource.first_name}'


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


def test_export_returns_the_report_as_xlsx(admin_client, report_data):
    response = admin_client.get(reverse('export_task_report', args=[MONTH]))

    assert response['Content-Type'] == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    assert response['Content-Disposition'] == 'attachment; filename="task_report_202506.xlsx"'
    ws = _read_sheet(response)
    assert ws.title == 'June 2025'

    blocks = _blocks(ws)
    assert set(blocks) == {_name(report_data['r1']), _name(report_data['r2'])}

    header, *rows = blocks[_name(report_data['r1'])]
    # like the page: name, scheduled days and hours, then day of week and day number for each day
    assert header[1] == 'Days 20'
    assert header[2] == 'Total HH 160'
    assert header[3] == 'Sun\n1'
    assert header[-1] == 'Mon\n30'
    assert len(header) == 3 + 30

    task_row = next(row for row in rows if row[0] == str(report_data['task_1']))
    assert task_row[2] == 8, 'numbers are stored as numbers'
    assert task_row[3 + 15] == 8, 'the hours of June 16th'
    assert [row[0] for row in rows] == [
        str(report_data['task_1']),
        'Total per day',
        'Night shift',
        'On call',
        'Travel',
        'Absences',
    ]


def test_export_shades_non_working_days(admin_client, report_data):
    ws = _read_sheet(admin_client.get(reverse('export_task_report', args=[MONTH])))

    # June 1st 2025 is a Sunday, June 2nd a public holiday in Italy, June 3rd a working day
    assert ws.cell(row=1, column=4).fill.fgColor.rgb == nwd_fill.fgColor.rgb
    assert ws.cell(row=2, column=4).fill.fgColor.rgb == nwd_fill.fgColor.rgb
    assert ws.cell(row=2, column=5).fill.fgColor.rgb == nwd_fill.fgColor.rgb
    assert ws.cell(row=2, column=6).fill.fgColor.rgb != nwd_fill.fgColor.rgb


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

    blocks = _blocks(_read_sheet(response))
    assert _name(report_data[included]) in blocks
    assert _name(report_data[excluded]) not in blocks


@pytest.mark.parametrize(
    ('query', 'has_absences'),
    [
        pytest.param({}, True, id='all-rows'),
        pytest.param({'tasks_only': '1'}, False, id='tasks-only'),
    ],
)
def test_export_honors_tasks_only(admin_client, report_data, query, has_absences):
    response = admin_client.get(reverse('export_task_report', args=[MONTH]), query)

    rows = _blocks(_read_sheet(response))[_name(report_data['r1'])]
    assert any(row[0] == 'Absences' for row in rows) is has_absences


def test_export_marks_resources_without_tasks(admin_client, report_data):
    idle = ContractFactory(period=(_dt('2020-01-01'), None)).resource

    response = admin_client.get(reverse('export_task_report', args=[MONTH]))

    _header, *rows = _blocks(_read_sheet(response))[_name(idle)]
    assert [row[0] for row in rows] == ['No tasks assigned']


def test_export_without_permission_contains_only_own_resource(resource_client, report_data):
    own = resource_client._resource
    ContractFactory(resource=own, period=(_dt('2020-01-01'), None))
    TaskFactory(title='Own task', resource=own, period=(_dt('2025-06-01'), None))

    # the filters are ignored for users who cannot see every resource
    response = resource_client.get(reverse('export_task_report', args=[MONTH]), {'resource': report_data['r1'].pk})

    assert set(_blocks(_read_sheet(response))) == {_name(own)}


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
