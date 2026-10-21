from datetime import date
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from testutils.factories import ContractFactory, DayEntryFactory, TimesheetSubmissionFactory

from krm3.core.models import Resource, TimesheetSubmission


def _entry(resource, contract, day, bank):
    return DayEntryFactory(
        resource=resource,
        contract=contract,
        day=day,
        day_hours=Decimal('16.00'),
        due_hours=Decimal('8.00'),
        bank=Decimal(bank),
    )


def _close(resource, period):
    return TimesheetSubmissionFactory(resource=resource, period=period, closed=True)


def test_frozen_balance_excludes_the_day_after_the_period_and_is_reused(monkeypatch):
    contract = ContractFactory(period=(date(2026, 9, 1), date(2026, 10, 1)))
    resource = contract.resource
    _entry(resource, contract, date(2026, 9, 7), '8.00')
    _entry(resource, contract, date(2026, 9, 10), '2.00')
    _entry(resource, contract, date(2026, 9, 30), '4.00')
    _entry(resource, contract, date(2026, 10, 1), '8.00')

    september = _close(resource, ('2026-09-01', '2026-10-01'))
    assert september.timesheet['bank_hours'] == '14.00'

    watermark_uses = []
    original = Resource._balance_from_watermark

    def spy(self, at, snapshots):
        result = original(self, at, snapshots)
        watermark_uses.append(result is not None)
        return result

    monkeypatch.setattr(Resource, '_balance_from_watermark', spy)

    assert resource.get_bank_hours_balance(date(2026, 10, 2)) == Decimal('22.00')
    assert watermark_uses == [True]


def test_falls_back_to_the_full_sum_when_the_snapshot_is_legacy():
    contract = ContractFactory(period=(date(2026, 9, 1), date(2026, 10, 1)))
    resource = contract.resource
    _entry(resource, contract, date(2026, 9, 7), '8.00')
    september = _close(resource, ('2026-09-01', '2026-10-01'))
    TimesheetSubmission.objects.filter(pk=september.pk).update(timesheet={'days': {}})

    _entry(resource, contract, date(2026, 10, 5), '3.00')

    assert resource.get_bank_hours_balance(date(2026, 10, 6)) == Decimal('11.00')


def test_falls_back_to_the_full_sum_when_nothing_is_closed_yet():
    contract = ContractFactory(period=(date(2026, 9, 1), date(2026, 10, 1)))
    resource = contract.resource
    _entry(resource, contract, date(2026, 9, 7), '8.00')
    _entry(resource, contract, date(2026, 9, 10), '2.00')

    assert resource.get_bank_hours_balance(date(2026, 9, 30)) == Decimal('10.00')


def test_closed_snapshot_is_authoritative_despite_earlier_open_entries():
    contract = ContractFactory(period=(date(2026, 8, 1), date(2026, 11, 1)))
    resource = contract.resource
    _entry(resource, contract, date(2026, 8, 15), '5.00')
    _entry(resource, contract, date(2026, 9, 7), '8.00')
    september = _close(resource, ('2026-09-01', '2026-10-01'))
    TimesheetSubmission.objects.filter(pk=september.pk).update(
        timesheet={**september.timesheet, 'bank_hours': '20.00'}
    )

    _entry(resource, contract, date(2026, 10, 5), '3.00')

    assert resource.get_bank_hours_balance(date(2026, 10, 6)) == Decimal('23.00')


def test_reopened_timesheet_is_not_used_as_a_watermark():
    contract = ContractFactory(period=(date(2026, 9, 1), date(2026, 10, 1)))
    resource = contract.resource
    _entry(resource, contract, date(2026, 9, 7), '8.00')
    september = _close(resource, ('2026-09-01', '2026-10-01'))
    assert september.timesheet['bank_hours'] == '8.00'

    september.closed = False
    september.save()
    _entry(resource, contract, date(2026, 9, 10), '8.00')

    assert resource.get_bank_hours_balance(date(2026, 9, 30)) == Decimal('16.00')


def test_later_timesheet_builds_on_the_earlier_frozen_balance():
    contract = ContractFactory(period=(date(2026, 9, 1), date(2026, 11, 1)))
    resource = contract.resource
    _entry(resource, contract, date(2026, 9, 7), '8.00')
    _entry(resource, contract, date(2026, 10, 5), '8.00')

    _close(resource, ('2026-09-01', '2026-10-01'))
    october = _close(resource, ('2026-10-01', '2026-11-01'))

    assert october.timesheet['bank_hours'] == '16.00'
    assert resource.get_bank_hours_balance(date(2026, 11, 1)) == Decimal('16.00')


def test_later_closed_submission_must_be_reopened_before_an_earlier_one():
    contract = ContractFactory(period=(date(2026, 9, 1), date(2026, 11, 1)))
    resource = contract.resource
    september_entry = _entry(resource, contract, date(2026, 9, 7), '8.00')
    september = _close(resource, ('2026-09-01', '2026-10-01'))
    _entry(resource, contract, date(2026, 10, 5), '8.00')
    october = _close(resource, ('2026-10-01', '2026-11-01'))

    september.closed = False
    with pytest.raises(ValidationError, match='A later timesheet is closed'):
        september.save()

    september.refresh_from_db()
    october.closed = False
    october.save()
    september.closed = False
    september.save()

    september_entry.__class__.objects.filter(pk=september_entry.pk).update(bank=Decimal('4.00'))
    september.closed = True
    september.save()
    october.closed = True
    october.save()

    assert september.timesheet['bank_hours'] == '4.00'
    assert october.timesheet['bank_hours'] == '12.00'
