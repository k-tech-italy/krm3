from datetime import date
from decimal import Decimal
from importlib import import_module
from types import SimpleNamespace

from django.apps import apps
from django.contrib.auth.models import Group
from django.db import connection
from testutils.factories import ContractFactory, DayEntryFactory, ResourceFactory, TimesheetSubmissionFactory

from krm3.core.models import TimesheetSubmission

migration = import_module('krm3.core.migrations.0033_timesheet_alignment_and_submission_rebuild')


def test_rebuild_closed_submissions_replaces_legacy_snapshots():
    resource = ResourceFactory()
    contract = ContractFactory(resource=resource, period=(date(2026, 9, 1), None))
    entry = DayEntryFactory(
        resource=resource, contract=contract, day=date(2026, 9, 6), day_hours=Decimal(6), bank=Decimal(6)
    )
    closed = TimesheetSubmissionFactory(resource=resource, period=(date(2026, 9, 1), date(2026, 10, 1)), closed=True)
    open_submission = TimesheetSubmissionFactory(
        resource=resource, period=(date(2026, 10, 1), date(2026, 11, 1)), closed=False
    )
    legacy_snapshot = {'days': {'2026-09-06': {'meal_voucher': 4}}, 'time_entries': [], 'bank_hours': '10.00'}
    TimesheetSubmission.objects.filter(pk=closed.pk).update(timesheet=legacy_snapshot)

    migration.rebuild_closed_submissions(apps, None)

    closed.refresh_from_db()
    open_submission.refresh_from_db()
    assert [day_entry['id'] for day_entry in closed.timesheet['day_entries']] == [entry.pk]
    assert 'time_entries' not in closed.timesheet
    # the bank balance frozen in the replaced snapshot is kept
    assert closed.timesheet['bank_hours'] == '10.00'
    assert open_submission.timesheet is None


def test_add_timesheet_group_permissions(db):
    viewer = Group.objects.create(name='Timesheet Viewer')
    manager = Group.objects.create(name='Timesheet Manager')
    administrator = Group.objects.create(name='Timesheet Administrator')

    migration.add_timesheet_group_permissions(apps, SimpleNamespace(connection=connection))

    def codenames(group):
        return set(group.permissions.values_list('content_type__app_label', 'codename'))

    assert codenames(viewer) == {('core', 'view_any_timesheet')}
    assert codenames(manager) == {
        ('core', 'manage_any_timesheet'),
        *(
            ('core', f'{action}_{model}')
            for model in ('taskentry', 'dayentry')
            for action in ('add', 'view', 'change', 'delete')
        ),
    }
    assert codenames(administrator) == {('core', 'manage_any_timesheet')}
