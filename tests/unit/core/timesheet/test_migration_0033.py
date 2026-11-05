from datetime import date
from decimal import Decimal
from importlib import import_module
from types import SimpleNamespace

import pytest
from django.apps import apps
from django.contrib.auth.models import Group
from django.db import connection
from testutils.factories import ContractFactory, DayEntryFactory, ResourceFactory, TimesheetSubmissionFactory

from krm3.core.models import DayEntry, TimesheetSubmission

migration = import_module('krm3.core.migrations.0033_timesheet_alignment_and_submission_rebuild')


@pytest.mark.parametrize(
    ('worked_hours', 'bank', 'closed', 'expected_meal_voucher'),
    [
        pytest.param('6.00', '6.00', True, 0, id='closed-all-hours-deposited'),
        pytest.param('6.00', '6.00', False, 0, id='open-all-hours-deposited'),
        pytest.param('6.00', '2.00', True, 1, id='remaining-hours-reach-threshold'),
        pytest.param('6.00', '3.00', True, 0, id='remaining-hours-below-threshold'),
        pytest.param('2.00', '-2.00', True, 1, id='withdrawal-reaches-threshold'),
    ],
)
def test_recompute_meal_vouchers_deducts_bank_deposits(worked_hours, bank, closed, expected_meal_voucher):
    contract = ContractFactory(
        period=(date(2026, 1, 1), None),
        meal_voucher={'mon': 6, 'tue': 6, 'wed': 6, 'thu': 6, 'fri': 6, 'sat': 4, 'sun': 4},
    )
    entry = DayEntryFactory(resource=contract.resource, contract=contract, day=date(2026, 10, 4))  # Sunday
    # the values 0032 left behind: the voucher was granted without deducting the deposit
    DayEntry.objects.filter(pk=entry.pk).update(
        day_hours=Decimal(worked_hours), bank=Decimal(bank), closed=closed, meal_voucher=1
    )

    migration.recompute_meal_vouchers(apps, None)

    entry.refresh_from_db()
    assert entry.meal_voucher == expected_meal_voucher


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
    assert codenames(administrator) == {('core', 'view_any_timesheet'), ('core', 'manage_any_timesheet')}
