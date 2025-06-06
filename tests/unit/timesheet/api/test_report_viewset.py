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
    assert str(task_1.resource), str(task_2.resource) in workbook.sheetnames
    sheet_1 = workbook[str(task_1.resource)]
    sheet_2 = workbook[str(task_2.resource)]

    # check row labels
    assert sheet_1['A1'].value == str(task_1.resource)
    assert sheet_1['A2'].value == 'Giorni'
    assert sheet_1['A3'].value == 'Is holiday'
    row_labels = [sheet_1[f'A{index}'].value for index in range(4, 13)]
    assert all(value in timeentry_key_mapping.values() for value in row_labels)

    # check week day labels
    assert sheet_1['C1'].value == 'Sun'
    assert sheet_1['AF1'].value == 'Mon'
    assert sheet_1['AG1'].value is None

    # check day labels
    assert sheet_1['C2'].value == 1
    assert sheet_1['AF2'].value == 30
    assert sheet_1['AG2'].value is None

    # check cell values
    assert sheet_1['L4'].value == 8
    assert sheet_1['Q4'].value is None
    assert sheet_2['O5'].value == 7

    # check total hours
    assert sheet_1['B4'].value == 14
    assert sheet_2['B5'].value == 7


@pytest.mark.django_db
def test_unauthorized_report_creation(api_client):
    url = reverse('timesheet-api:api-report-monthly-report', args=['202506'])
    client = api_client()
    response = client.get(url)
    assert response.status_code == 401
