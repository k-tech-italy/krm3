from decimal import Decimal

from bs4 import BeautifulSoup
from django.urls import reverse
from testutils.date_utils import _dt
from testutils.factories import ContractFactory, DayEntryFactory, ResourceFactory, SpecialLeaveReasonFactory


def _get_resource_table(response, resource):
    soup = BeautifulSoup(response.content, 'html.parser')
    for table in soup.find_all('table', class_='report-table'):
        header = table.find('td', class_='row-header')
        if header and resource.first_name in header.get_text() and resource.last_name in header.get_text():
            return table
    return None


def _get_report_rows(table):
    return {
        row.find('td', class_='row-header').get_text(strip=True): [
            cell.get_text(strip=True) for cell in row.find_all('td', class_='cell-data')
        ]
        for row in table.find_all('tr', class_='row-data')
        if row.find('td', class_='row-header')
    }


def test_timesheet_report_shows_day_entry_hours_and_totals(admin_client):
    contract = ContractFactory()
    resource = contract.resource
    DayEntryFactory(
        contract=contract,
        resource=resource,
        day=_dt('2025-06-05'),
        due_hours=Decimal('8'),
        day_hours=Decimal('6'),
        travel_hours=Decimal('2'),
    )

    response = admin_client.get(reverse('report-month', args=['202506']))

    assert response.status_code == 200
    table = _get_resource_table(response, resource)
    assert table is not None
    rows = _get_report_rows(table)
    assert rows['Regular hours'][0] == '8'
    assert rows['Regular hours'][5] == '8'
    assert rows['Day shift hours'][0] == '6'
    assert rows['Travel'][0] == '2'


def test_timesheet_report_only_shows_preferred_resources_to_privileged_users(admin_client):
    preferred = ResourceFactory(preferred_in_report=True)
    hidden = ResourceFactory(preferred_in_report=False)
    ContractFactory(resource=preferred)
    ContractFactory(resource=hidden)

    response = admin_client.get(reverse('report-month', args=['202506']))

    assert response.status_code == 200
    assert _get_resource_table(response, preferred) is not None
    assert _get_resource_table(response, hidden) is None


def test_timesheet_report_shows_sick_protocol_and_special_leave(admin_client):
    contract = ContractFactory()
    resource = contract.resource
    reason = SpecialLeaveReasonFactory(title='Parental leave')
    DayEntryFactory(
        contract=contract,
        resource=resource,
        day=_dt('2025-06-09'),
        due_hours=Decimal('8'),
        is_sick=True,
        protocol_number='SICK-123',
    )
    DayEntryFactory(
        contract=contract,
        resource=resource,
        day=_dt('2025-06-10'),
        due_hours=Decimal('8'),
        special_leave_hours=Decimal('4'),
        special_leave_reason=reason,
    )

    response = admin_client.get(reverse('report-month', args=['202506']))

    assert response.status_code == 200
    table = _get_resource_table(response, resource)
    assert table is not None
    rows = _get_report_rows(table)
    assert rows['Sick SICK-123'][0] == '8'
    assert rows['Sick SICK-123'][9] == '8'
    assert rows['Special leave (Parental leave)'][0] == '4'
    assert rows['Special leave (Parental leave)'][10] == '4'


def test_timesheet_report_marks_holidays_as_non_working_days(admin_client):
    contract = ContractFactory()
    resource = contract.resource
    DayEntryFactory(
        contract=contract,
        resource=resource,
        day=_dt('2025-06-02'),
        due_hours=Decimal('0'),
        is_holiday=True,
    )

    response = admin_client.get(reverse('report-month', args=['202506']))

    assert response.status_code == 200
    table = _get_resource_table(response, resource)
    assert table is not None
    holiday_row = next(
        row
        for row in table.find_all('tr', class_='row-data')
        if row.find('td', class_='row-header').get_text(strip=True) == 'Holiday'
    )
    day_cell = holiday_row.find_all('td', class_='cell-data')[2]
    assert 'non-workday' in day_cell.get('class', [])


def test_resource_can_see_their_empty_timesheet_report_when_not_preferred(client):
    resource = ResourceFactory(preferred_in_report=False)
    ContractFactory(resource=resource)
    client.login(username=resource.user.username, password=resource.user._password)

    response = client.get(reverse('report-month', args=['202506']))

    assert response.status_code == 200
    table = _get_resource_table(response, resource)
    assert table is not None
    assert 'No time entries available' in table.get_text()
