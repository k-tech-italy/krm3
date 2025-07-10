import datetime
import io

import pytest
import openpyxl
from django.urls import reverse
from testutils.factories import (
    TaskFactory,
    TimeEntryFactory,
)

from src.krm3.timesheet.report import timeentry_key_mapping
from django.contrib.auth.models import Permission


@pytest.mark.django_db
def test_report_creation(api_client, regular_user):
    task_1 = TaskFactory()
    task_2 = TaskFactory()

    TimeEntryFactory(
        date=datetime.date(2025, 6, 10),
        day_shift_hours=8,
        task=task_1,
        resource=task_1.resource,
    )
    TimeEntryFactory(
        date=datetime.date(2025, 6, 12),
        day_shift_hours=6,
        task=task_1,
        resource=task_1.resource,
    )

    TimeEntryFactory(
        date=datetime.date(2025, 6, 13),
        night_shift_hours=7,
        task=task_1,
        resource=task_2.resource,
    )

    url = reverse('timesheet-api:api-report-export-report', args=['202506'])
    client = api_client(user=regular_user)
    response = client.get(url)
    assert response.status_code == 200
    assert (
        response['Content-Type']
        == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

    workbook = openpyxl.load_workbook(filename=io.BytesIO(response.content))

    # check sheet names
    r1_name = f'{task_1.resource.last_name.upper()} {task_1.resource.first_name}'
    r2_name = f'{task_2.resource.last_name.upper()} {task_2.resource.first_name}'
    assert r1_name, r2_name in workbook.sheetnames
    sheet_1 = workbook[r1_name]
    sheet_2 = workbook[r2_name]

    # check row labels
    assert sheet_1['A1'].value == r1_name
    assert sheet_1['A2'].value == 'Giorni'
    row_labels = [sheet_1[f'A{index}'].value for index in range(3, 12)]
    assert all(value in timeentry_key_mapping.values() for value in row_labels)

    # check day labels
    assert sheet_1['C2'].value == 'Sun\n1'
    assert sheet_1['AF2'].value == 'Mon\n30'
    assert sheet_1['AG2'].value is None

    # check cell values
    assert sheet_1['L3'].value == 8
    assert sheet_1['Q3'].value is None
    assert sheet_2['O4'].value == 7

    # check total hours
    assert sheet_1['B3'].value == 14
    assert sheet_2['B4'].value == 7


@pytest.mark.django_db
def test_unauthorized_report_creation(api_client):
    url = reverse('timesheet-api:api-report-export-report', args=['202506'])
    client = api_client()
    response = client.get(url)
    assert response.status_code == 401


def test_data_report_user_without_permissions(api_client, regular_user):
    url = reverse('timesheet-api:api-report-data-report', args=['202506'])
    client = api_client(user=regular_user)
    response = client.get(url)
    assert response.status_code == 403


def test_data_report_wrong_date(api_client, admin_user):
    url = reverse('timesheet-api:api-report-data-report', args=['314159'])
    client = api_client(user=admin_user)
    response = client.get(url)
    assert response.status_code == 400
    assert response.json() == {'error': 'Invalid date.'}


@pytest.mark.django_db
@pytest.mark.parametrize(
    'permissions',
    [
        pytest.param(['manage_any_timesheet']),
        pytest.param(['view_any_timesheet']),
        pytest.param(['view_any_timesheet', 'manage_any_timesheet']),
    ],
)
def test_data_report_success_user_with_permissions(
    api_client, regular_user, permissions
):
    for permission in permissions:
        regular_user.user_permissions.add(Permission.objects.get(codename=permission))
    url = reverse('timesheet-api:api-report-data-report', args=['202506'])
    client = api_client(user=regular_user)
    response = client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_data_report_success_admin(api_client, admin_user):
    url = reverse('timesheet-api:api-report-data-report', args=['202506'])
    client = api_client(user=admin_user)
    response = client.get(url)
    assert response.status_code == 200
