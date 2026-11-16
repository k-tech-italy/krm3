from datetime import date, timedelta
from unittest.mock import patch

import pytest
from django.contrib import admin
from django.test import RequestFactory
from django.urls import reverse
from testutils.factories import DayEntryFactory, ResourceFactory, TaskEntryFactory, TimesheetSubmissionFactory

from krm3.core.models import TaskEntry, TimesheetSubmission
from krm3.timesheet.admin import DayEntryAdmin, TaskEntryAdmin


def test_admin_cannot_change_or_delete_entries_in_closed_submission(admin_user):
    day_entry = DayEntryFactory()
    task_entry = TaskEntryFactory(day_entry=day_entry, resource=day_entry.resource)
    day_entry.day_hours = day_entry.contract.get_due_hours(day_entry.day)
    day_entry.save()
    TimesheetSubmissionFactory(
        resource=day_entry.resource,
        period=(day_entry.day, day_entry.day + timedelta(days=1)),
        status=TimesheetSubmission.Status.CLOSED,
    )
    day_entry.refresh_from_db()
    task_entry.refresh_from_db()

    request = RequestFactory().get('/')
    request.user = admin_user
    day_entry_admin = DayEntryAdmin(model=day_entry.__class__, admin_site=None)
    task_entry_admin = TaskEntryAdmin(model=task_entry.__class__, admin_site=None)

    assert day_entry_admin.has_change_permission(request, day_entry) is False
    assert day_entry_admin.has_delete_permission(request, day_entry) is False
    assert task_entry_admin.has_change_permission(request, task_entry) is False
    assert task_entry_admin.has_delete_permission(request, task_entry) is False


@pytest.mark.parametrize(
    ('params', 'expected'),
    [
        pytest.param('', {'jan', 'feb'}, id='no-filter'),
        pytest.param('?period__range__gte=2025-02-01', {'feb'}, id='lower-only'),
        pytest.param('?period__range__lte=2025-01-31', {'jan'}, id='upper-only'),
        pytest.param(
            '?period__range__gte=2025-01-15&period__range__lte=2025-02-15', {'jan', 'feb'}, id='overlapping-both'
        ),
        pytest.param('?period__range__gte=random&period__range__lte=string', set(), id='invalid-dates'),
    ],
)
def test_timesheet_submission_changelist_period_filter(admin_client, params, expected):
    submissions = {
        'jan': TimesheetSubmissionFactory(period=(date(2025, 1, 1), date(2025, 2, 1))),
        'feb': TimesheetSubmissionFactory(period=(date(2025, 2, 1), date(2025, 3, 1))),
    }

    response = admin_client.get(reverse('admin:core_timesheetsubmission_changelist') + params)

    assert response.status_code == 200
    shown = {obj.pk for obj in response.context['cl'].result_list}
    assert shown == {submissions[key].pk for key in expected}


def test_timesheet_submission_view_entries_redirects_to_filtered_task_entries(admin_client):
    included_entry = TaskEntryFactory(day=True)
    included_entry.day_entry.day_hours = included_entry.day_entry.contract.get_due_hours(included_entry.day_entry.day)
    included_entry.day_entry.save()
    submission = TimesheetSubmissionFactory(
        period=(included_entry.day_entry.day, included_entry.day_entry.day + timedelta(days=1)),
        resource=included_entry.day_entry.resource,
    )
    excluded_entry = TaskEntryFactory(day=True)
    excluded_entry.day_entry.day_hours = excluded_entry.day_entry.contract.get_due_hours(excluded_entry.day_entry.day)
    excluded_entry.day_entry.save()
    TimesheetSubmissionFactory(
        period=(excluded_entry.day_entry.day, excluded_entry.day_entry.day + timedelta(days=1)),
        resource=excluded_entry.day_entry.resource,
    )
    response = admin_client.get(reverse('admin:core_timesheetsubmission_view_entries', args=[submission.pk]))

    expected_url = reverse('admin:core_taskentry_changelist') + f'?day_entry__timesheet_id={submission.pk}'
    assert response.url == expected_url

    response = admin_client.get(response.url)
    assert response.status_code == 200
    assert [obj.pk for obj in response.context['cl'].result_list] == [included_entry.pk]


def test_admin_can_approve_pending_submission(admin_client):
    submission = TimesheetSubmissionFactory(status=TimesheetSubmission.Status.PENDING)

    response = admin_client.get(reverse('admin:core_timesheetsubmission_approve', args=[submission.pk]))

    assert response.status_code == 302
    submission.refresh_from_db()
    assert submission.status == TimesheetSubmission.Status.CLOSED


def test_admin_can_reject_pending_submission_with_message(admin_client):
    submission = TimesheetSubmissionFactory(status=TimesheetSubmission.Status.PENDING)
    url = reverse('admin:core_timesheetsubmission_reject', args=[submission.pk])

    response = admin_client.post(url, {'message': 'Please correct the bank hours.'})

    assert response.status_code == 302
    submission.refresh_from_db()
    assert submission.status == TimesheetSubmission.Status.REJECTED
    assert submission.rejection_message == 'Please correct the bank hours.'


def test_reject_requires_a_message(admin_client):
    submission = TimesheetSubmissionFactory(status=TimesheetSubmission.Status.PENDING)
    url = reverse('admin:core_timesheetsubmission_reject', args=[submission.pk])

    response = admin_client.post(url, {'message': ''})

    assert response.status_code == 200
    submission.refresh_from_db()
    assert submission.status == TimesheetSubmission.Status.PENDING


def test_admin_can_reopen_closed_submission(admin_client):
    submission = TimesheetSubmissionFactory(status=TimesheetSubmission.Status.CLOSED)

    response = admin_client.get(reverse('admin:core_timesheetsubmission_reopen', args=[submission.pk]))

    assert response.status_code == 302
    submission.refresh_from_db()
    assert submission.status == TimesheetSubmission.Status.DRAFT


@pytest.mark.parametrize(
    ('missing_field', 'data'),
    [
        pytest.param(
            'resource',
            {'period_0': '2026-11-01', 'period_1': '2026-11-30', 'status': 'closed'},
            id='missing-resource',
        ),
        pytest.param(
            'period',
            {'status': 'closed'},
            id='missing-period',
        ),
    ],
)
def test_timesheet_submission_add_reports_missing_required_fields(admin_client, missing_field, data):
    if missing_field != 'resource':
        data['resource'] = ResourceFactory().pk

    response = admin_client.post(reverse('admin:core_timesheetsubmission_add'), data)

    assert response.status_code == 200
    assert response.context['adminform'].form.errors[missing_field] == ['This field is required.']
    assert not TimesheetSubmission.objects.exists()


def test_task_entry_admin_delegates_other_lookups_to_model_admin():
    request = RequestFactory().get('/')
    task_entry_admin = TaskEntryAdmin(model=TaskEntry, admin_site=None)

    with patch.object(admin.ModelAdmin, 'lookup_allowed', return_value=False) as lookup_allowed:
        result = task_entry_admin.lookup_allowed('task__project', '1', request)

    assert result is False
    lookup_allowed.assert_called_once_with('task__project', '1', request)
