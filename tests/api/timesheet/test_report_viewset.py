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


@pytest.mark.django_db
def test_report_creation(api_client, regular_user):
    task_1 = TaskFactory()
    task_2 = TaskFactory()

    TimeEntryFactory(date=datetime.date(2025, 6,10),
                             day_shift_hours=8, task=task_1, resource=task_1.resource)
    TimeEntryFactory(date=datetime.date(2025, 6,12),
                             day_shift_hours=6, task=task_1, resource=task_1.resource)

    TimeEntryFactory(date=datetime.date(2025, 6,13),
                             night_shift_hours=7, task=task_1, resource=task_2.resource)

    url = reverse('timesheet-api:api-report-monthly-report', args=['202506'])
    client = api_client(user=regular_user)
    response = client.get(url)
    assert response.status_code == 200
    assert response['Content-Type'] == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

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
    url = reverse('timesheet-api:api-report-monthly-report', args=['202506'])
    client = api_client()
    response = client.get(url)
    assert response.status_code == 401
