from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth.models import Permission
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from psycopg.types.range import DateRange
from testutils.factories import (
    ContractFactory,
    DayEntryFactory,
    ProjectFactory,
    ResourceFactory,
    TaskEntryFactory,
    TaskFactory,
    TimesheetSubmissionFactory,
    UserFactory,
    create_contract_without_scheduled_hours,
)

from krm3.core.forms import ContractTerminationForm
from krm3.core.models import Contract, DayEntry, Task, TaskEntry, TimesheetSubmission
from krm3.core.termination import ContractModifiedError, ContractTermination

TERMINATION_DATE = date(2026, 11, 15)


def _month(year: int, month: int) -> tuple[date, date]:
    return date(year, month, 1), date(year + month // 12, month % 12 + 1, 1)


@pytest.fixture
def scenario():
    """An open contract from 2026-01-01, with data before and after 2026-11-15."""
    resource = ResourceFactory()
    contract = create_contract_without_scheduled_hours(resource, (date(2026, 1, 1), None))
    project = ProjectFactory(period=(date(2020, 1, 1), None))

    def task(title: str, start: date, end: date | None) -> Task:
        return TaskFactory(title=title, project=project, resource=resource, period=(start, end))

    tasks = {
        'ended': task('ended', date(2026, 1, 1), date(2026, 6, 1)),
        'ends-on-termination': task('ends-on-termination', date(2026, 1, 1), date(2026, 11, 16)),
        'open': task('open', date(2026, 2, 1), None),
        'ends-later': task('ends-later', date(2026, 3, 1), date(2027, 1, 1)),
        'starts-on-termination': task('starts-on-termination', TERMINATION_DATE, None),
        'starts-later': task('starts-later', date(2026, 11, 20), None),
    }

    def entry(day: date, task: Task) -> DayEntry:
        day_entry = DayEntryFactory(resource=resource, contract=contract, day=day, day_hours=Decimal(8))
        TaskEntryFactory(day_entry=day_entry, task=task, day_shift_hours=8)
        return day_entry

    entries = {
        'kept': entry(date(2026, 11, 14), tasks['open']),
        'on-termination': entry(TERMINATION_DATE, tasks['starts-on-termination']),
        'november': entry(date(2026, 11, 16), tasks['open']),
        'later-task': entry(date(2026, 11, 21), tasks['starts-later']),
        'december': entry(date(2026, 12, 2), tasks['ends-later']),
    }

    submissions = {
        'october': TimesheetSubmissionFactory(resource=resource, period=_month(2026, 10), closed=True),
        'november': TimesheetSubmissionFactory(resource=resource, period=_month(2026, 11), closed=True),
        'december': TimesheetSubmissionFactory(resource=resource, period=_month(2026, 12), closed=True),
        'january': TimesheetSubmissionFactory(resource=resource, period=_month(2027, 1), closed=False),
    }
    return {'contract': contract, 'tasks': tasks, 'entries': entries, 'submissions': submissions}


def test_termination_lists_what_follows_the_termination_date(scenario):
    termination = ContractTermination(scenario['contract'], TERMINATION_DATE)
    tasks = scenario['tasks']
    submissions = scenario['submissions']

    assert list(termination.day_entries().values_list('day', flat=True)) == [
        date(2026, 11, 16),
        date(2026, 11, 21),
        date(2026, 12, 2),
    ]
    assert list(termination.deleted_tasks()) == [tasks['starts-later']]
    assert set(termination.truncated_tasks()) == {tasks['open'], tasks['ends-later'], tasks['starts-on-termination']}
    assert list(termination.deleted_submissions()) == [submissions['december'], submissions['january']]
    assert list(termination.truncated_submissions()) == [submissions['november']]


def test_apply_termination(scenario):
    contract = scenario['contract']
    tasks = scenario['tasks']
    entries = scenario['entries']
    submissions = scenario['submissions']
    october_snapshot = submissions['october'].timesheet

    outcome = ContractTermination(contract, TERMINATION_DATE).apply(contract.version)

    assert (
        outcome.day_entries,
        outcome.deleted_tasks,
        outcome.truncated_tasks,
        outcome.deleted_submissions,
        outcome.truncated_submissions,
    ) == (3, 1, 3, 2, 1)

    contract.refresh_from_db()
    assert contract.period == DateRange(date(2026, 1, 1), date(2026, 11, 16), '[)')

    assert set(DayEntry.objects.values_list('pk', flat=True)) == {entries['kept'].pk, entries['on-termination'].pk}
    assert set(TaskEntry.objects.values_list('day_entry__day', flat=True)) == {date(2026, 11, 14), TERMINATION_DATE}

    assert not Task.objects.filter(pk=tasks['starts-later'].pk).exists()
    periods = {task.title: task.period for task in Task.objects.all()}
    assert periods == {
        'ended': DateRange(date(2026, 1, 1), date(2026, 6, 1), '[)'),
        'ends-on-termination': DateRange(date(2026, 1, 1), date(2026, 11, 16), '[)'),
        'open': DateRange(date(2026, 2, 1), date(2026, 11, 16), '[)'),
        'ends-later': DateRange(date(2026, 3, 1), date(2026, 11, 16), '[)'),
        'starts-on-termination': DateRange(TERMINATION_DATE, date(2026, 11, 16), '[)'),
    }

    assert set(TimesheetSubmission.objects.values_list('pk', flat=True)) == {
        submissions['october'].pk,
        submissions['november'].pk,
    }
    october = TimesheetSubmission.objects.get(pk=submissions['october'].pk)
    assert october.timesheet == october_snapshot
    november = TimesheetSubmission.objects.get(pk=submissions['november'].pk)
    assert november.period == DateRange(date(2026, 11, 1), date(2026, 11, 16), '[)')
    assert november.closed is True
    # the rebuilt snapshot no longer holds the deleted days
    assert sorted(day_entry['day'] for day_entry in november.timesheet['day_entries']) == [
        '2026-11-14',
        '2026-11-15',
    ]
    assert set(november.dayentry_set.values_list('day', flat=True)) == {date(2026, 11, 14), TERMINATION_DATE}


def test_apply_termination_without_data_after_the_date():
    contract = ContractFactory(period=(date(2026, 1, 1), None))

    outcome = ContractTermination(contract, TERMINATION_DATE).apply(contract.version)

    assert outcome.day_entries == outcome.deleted_tasks == outcome.truncated_tasks == 0
    assert outcome.deleted_submissions == outcome.truncated_submissions == 0
    contract.refresh_from_db()
    assert contract.period.upper == date(2026, 11, 16)


def test_apply_locks_the_contract_with_the_version_read_before_any_change(scenario):
    contract = scenario['contract']
    version = contract.version

    with CaptureQueriesContext(connection) as queries:
        ContractTermination(contract, TERMINATION_DATE).apply(version)

    statements = [query['sql'] for query in queries.captured_queries]
    first_change = next(i for i, sql in enumerate(statements) if sql.startswith(('UPDATE', 'DELETE', 'INSERT')))
    lock = next(i for i, sql in enumerate(statements) if sql.endswith('FOR UPDATE'))
    assert lock < first_change
    assert f'"core_contract"."version" = {version}' in statements[lock]
    contract.refresh_from_db()
    assert contract.version != version


def test_apply_with_a_stale_version_changes_nothing(scenario):
    contract = scenario['contract']
    stale_version = contract.version
    Contract.objects.get(pk=contract.pk).save()  # someone else changes the contract

    with pytest.raises(ContractModifiedError):
        ContractTermination(contract, TERMINATION_DATE).apply(stale_version)

    contract.refresh_from_db()
    assert contract.period.upper is None
    assert DayEntry.objects.count() == 5
    assert Task.objects.count() == 6
    assert TimesheetSubmission.objects.count() == 4


@pytest.mark.parametrize(
    ('termination_date', 'valid'),
    [
        pytest.param(date(2025, 12, 31), False, id='before-start'),
        pytest.param(date(2026, 1, 1), True, id='on-start'),
        pytest.param(date(2026, 11, 15), True, id='after-start'),
    ],
)
def test_termination_date_cannot_precede_the_contract_start(db, termination_date, valid):
    contract = ContractFactory(period=(date(2026, 1, 1), None))

    form = ContractTerminationForm(
        {'termination_date': termination_date, 'version': contract.version}, contract=contract
    )

    assert form.is_valid() is valid


def _terminate_url(contract: Contract) -> str:
    return reverse('admin:core_contract_terminate', args=[contract.pk])


def test_admin_terminate_asks_for_confirmation_before_changing_anything(krm3app, admin_user, scenario):
    contract = scenario['contract']
    page = krm3app.get(_terminate_url(contract), user=admin_user)

    form = page.forms['contract-termination-form']
    form['termination_date'] = TERMINATION_DATE.isoformat()
    confirmation = form.submit()

    assert confirmation.status_code == 200
    text = confirmation.text
    for day in ('2026-11-16', '2026-11-21', '2026-12-02'):
        assert day in text
    assert '2026-11-14' not in text
    assert str(scenario['tasks']['starts-later']) in text
    assert str(scenario['tasks']['open']) in text
    assert '2026-11-01 - 2026-11-30 (closed)' in text
    assert '2026-12-01 - 2026-12-31 (closed)' in text
    assert '2027-01-01 - 2027-01-31' in text
    # nothing changes until the termination is confirmed
    contract.refresh_from_db()
    assert contract.period.upper is None
    assert DayEntry.objects.count() == 5

    # the version read when the termination was started is carried to the final confirmation
    assert confirmation.forms['contract-termination-confirm']['version'].value == str(contract.version)

    result = confirmation.forms['contract-termination-confirm'].submit().follow()

    assert 'Contract terminated on 2026-11-15' in result.text
    contract.refresh_from_db()
    assert contract.period.upper == date(2026, 11, 16)
    assert DayEntry.objects.count() == 2


def test_admin_terminate_rejects_a_date_before_the_contract_start(krm3app, admin_user):
    contract = ContractFactory(period=(date(2026, 1, 1), None))
    form = krm3app.get(_terminate_url(contract), user=admin_user).forms['contract-termination-form']
    form['termination_date'] = '2025-12-31'

    page = form.submit()

    assert page.status_code == 200
    assert 'it cannot end before' in page.text
    contract.refresh_from_db()
    assert contract.period.upper is None


def test_admin_terminate_refuses_if_the_contract_changed_after_the_button_was_pressed(krm3app, admin_user, scenario):
    contract = scenario['contract']
    form = krm3app.get(_terminate_url(contract), user=admin_user).forms['contract-termination-form']
    form['termination_date'] = TERMINATION_DATE.isoformat()
    confirmation = form.submit()

    changed = Contract.objects.get(pk=contract.pk)
    changed.working_schedule = {'mon': 4, 'tue': 4, 'wed': 4, 'thu': 4, 'fri': 4, 'sat': 0, 'sun': 0}
    changed.save()

    response = confirmation.forms['contract-termination-confirm'].submit()

    assert response.status_code == 302
    assert response.location == _terminate_url(contract)
    assert 'it was changed after the termination was started' in response.follow().text
    contract.refresh_from_db()
    assert contract.period.upper is None
    assert DayEntry.objects.count() == 5
    assert Task.objects.count() == 6


@pytest.mark.parametrize(
    ('permissions', 'status_code'),
    [
        pytest.param([], 403, id='no-permission'),
        pytest.param(['view_contract'], 403, id='view-only'),
        pytest.param(['view_contract', 'change_contract'], 200, id='change'),
    ],
)
def test_admin_terminate_requires_the_change_permission(krm3app, permissions, status_code):
    user = UserFactory(is_staff=True)
    user.user_permissions.add(*Permission.objects.filter(content_type__app_label='core', codename__in=permissions))
    contract = ContractFactory(period=(date(2026, 1, 1), None))

    response = krm3app.get(_terminate_url(contract), user=user, expect_errors=True)

    assert response.status_code == status_code
