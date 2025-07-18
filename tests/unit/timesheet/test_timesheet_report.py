"""
Hint: keep the file ./test_timesheet_report.xlsx aligned with fixture report_resource
"""

import pathlib
from decimal import Decimal as D  # noqa: N817

import pytest

from krm3.timesheet.report import timesheet_report_raw_data, calculate_overtime, timeentry_key_mapping, \
    get_submitted_dates, get_days_submission
from krm3.utils.dates import dt, KrmDay
from testutils import yaml as test_yaml
from testutils.factories import TimeEntryFactory, TaskFactory, SpecialLeaveReasonFactory

from tests._extras.testutils.factories import TimesheetSubmissionFactory


@pytest.fixture
def report_resource():
    sl1 = SpecialLeaveReasonFactory(id=1)
    sl2 = SpecialLeaveReasonFactory(id=2)
    t1 = TaskFactory()
    r1 = t1.resource
    t2 = TaskFactory(resource=r1)
    r1._time_entries = [
        TimeEntryFactory(resource=r1, date='2025-05-30', day_shift_hours=0, holiday_hours=8),
        TimeEntryFactory(
            resource=r1, date='2025-05-31', task=t1, day_shift_hours=0.5, night_shift_hours=1, travel_hours=2
        ),
        TimeEntryFactory(resource=r1, date='2025-05-31', task=t2, day_shift_hours=6, night_shift_hours=1.5),
        TimeEntryFactory(resource=r1, date='2025-06-01', day_shift_hours=0, sick_hours=8),
        TimeEntryFactory(resource=r1, date='2025-06-02', task=t1, day_shift_hours=0, on_call_hours=1),
        TimeEntryFactory(resource=r1, date='2025-06-02', task=t2, day_shift_hours=0, travel_hours=2),
        TimeEntryFactory(
            resource=r1, date='2025-06-03', task=t2, day_shift_hours=4, night_shift_hours=3, on_call_hours=10
        ),
        TimeEntryFactory(resource=r1, date='2025-06-04', day_shift_hours=0, leave_hours=1.5),
        TimeEntryFactory(
            resource=r1, date='2025-06-05', day_shift_hours=0, special_leave_hours=0.5, special_leave_reason=sl1
        ),
        TimeEntryFactory(
            resource=r1, date='2025-06-06', day_shift_hours=0, special_leave_hours=5, special_leave_reason=sl2
        ),
    ]
    return r1


def _raw_results():
    return {
        'day_shift': [D('0.00'), D('6.50'), D('0.00'), D('0.00'), D('4.00'), D('0.00'), D('0.00'), D('0.00')],
        'night_shift': [D('0.00'), D('2.50'), D('0.00'), D('0.00'), D('3.00'), D('0.00'), D('0.00'), D('0.00')],
        'on_call': [D('0.00'), D('0.00'), D('0.00'), D('1.00'), D('10.00'), D('0.00'), D('0.00'), D('0.00')],
        'travel': [D('0.00'), D('2.00'), D('0.00'), D('2.00'), D('0.00'), D('0.00'), D('0.00'), D('0.00')],
        'holiday': [D('8.00'), D('0.00'), D('0.00'), D('0.00'), D('0.00'), D('0.00'), D('0.00'), D('0.00')],
        'leave': [D('0.00'), D('0.00'), D('0.00'), D('0.00'), D('0.00'), D('1.50'), D('0.00'), D('0.00')],
        'rest': [D('0.00'), D('0.00'), D('0.00'), D('0.00'), D('0.00'), D('0.00'), D('0.00'), D('0.00')],
        'special_leave|0': [D('0.00'), D('0.00'), D('0.00'), D('0.00'), D('0.00'), D('0.00'), D('0.50'), D('0.00')],
        'special_leave|1': [D('0.00'), D('0.00'), D('0.00'), D('0.00'), D('0.00'), D('0.00'), D('0.00'), D('5.00')],
        'sick': [D('0.00'), D('0.00'), D('8.00'), D('0.00'), D('0.00'), D('0.00'), D('0.00'), D('0.00')],
        'overtime': [D('0.00'), D('0.00'), D('0.00'), D('0.00'), D('0.00'), D('0.00'), D('0.00'), D('0.00')],
        'days': [KrmDay('2025-05-30'), KrmDay('2025-05-31'), KrmDay('2025-06-01'), KrmDay('2025-06-02'),
            KrmDay('2025-06-03'), KrmDay('2025-06-04'), KrmDay('2025-06-05'), KrmDay('2025-06-06')],
    }


_overtime_results = {
    'day_shift': [D('0.00'), D('8.00'), D('0.00'), D('0.00'), D('7.00'), D('0.00'), D('0.00'), D('0.00')],
    'night_shift': [D('0.00'), D('2.50'), D('0.00'), D('0.00'), D('3.00'), D('0.00'), D('0.00'), D('0.00')],
    'on_call': [D('0.00'), D('0.00'), D('0.00'), D('1.00'), D('10.00'), D('0.00'), D('0.00'), D('0.00')],
    'travel': [D('0.00'), D('2.00'), D('0.00'), D('2.00'), D('0.00'), D('0.00'), D('0.00'), D('0.00')],
    'holiday': [D('8.00'), D('0.00'), D('0.00'), D('0.00'), D('0.00'), D('0.00'), D('0.00'), D('0.00')],
    'leave': [D('0.00'), D('0.00'), D('0.00'), D('0.00'), D('0.00'), D('1.50'), D('0.00'), D('0.00')],
    'rest': [D('0.00'), D('0.00'), D('0.00'), D('0.00'), D('0.00'), D('0.00'), D('0.00'), D('0.00')],
    'special_leave|0': [D('0.00'), D('0.00'), D('0.00'), D('0.00'), D('0.00'), D('0.00'), D('0.50'), D('0.00')],
    'special_leave|1': [D('0.00'), D('0.00'), D('0.00'), D('0.00'), D('0.00'), D('0.00'), D('0.00'), D('5.0')],
    'sick': [D('0.00'), D('0.00'), D('8.00'), D('0.00'), D('0.00'), D('0.00'), D('0.00'), D('0.00')],
    'overtime': [D('0.00'), D('3.00'), D('0.00'), D('0.00'), D('0.00'), D('0.00'), D('0.00'), D('0.00')],
    'days': [KrmDay('2025-05-30'), KrmDay('2025-05-31'), KrmDay('2025-06-01'), KrmDay('2025-06-02'),
            KrmDay('2025-06-03'), KrmDay('2025-06-04'), KrmDay('2025-06-05'), KrmDay('2025-06-06')],
}


class TestTimesheetReport:
    @pytest.mark.parametrize(
        ('data', 'expected'),
        test_yaml.generate_parameters(pathlib.Path(__file__).parent / 'testcases/timesheet_report'),
    )
    def test_report_daysum(self, data: dict, expected):
        data = {k: [D(f'{float(v):02}')] for k, v in data.items()}
        expected = {k: [D(f'{float(v):02}')] for k, v in expected.items()}
        result_base = {k: [D('0.00')] for k in _overtime_results if not k.startswith('special')}
        data = result_base | data
        expected_dict = {timeentry_key_mapping.get(k, k): v for k, v in result_base.items()} | expected

        data = {'<resource>': data}
        calculate_overtime(data)
        result = {timeentry_key_mapping.get(k, k): v for k, v in data['<resource>'].items()}
        assert result == expected_dict

    def test_report_raw_data(self, report_resource):
        from krm3.core.models import TimeEntry

        assert TimeEntry.objects.count() == report_resource._time_entries.__len__()
        result, additional_key_mapping = timesheet_report_raw_data(dt('2025-05-30'), dt('2025-06-06'))
        dynamic_special_leave_keys = additional_key_mapping.keys()
        expected_result =_raw_results()
        for index, key in enumerate(dynamic_special_leave_keys):
            expected_result[key] = expected_result[f"special_leave|{index}"]
            del expected_result[f"special_leave|{index}"]
        assert result == {report_resource: expected_result}

    def test_calculate_overtime(self):
        results = {'<resource>': _raw_results()}
        calculate_overtime(results)
        assert results['<resource>'] == _overtime_results


class TestTimesheetSubmission:
    """Test timesheet submission functionality"""

    def test_get_submitted_dates_no_submissions(self, report_resource):
        """Test get_submitted_dates when no submissions exist"""
        from_date = dt('2025-5-30')
        to_date = dt('2025-6-5')

        submitted_dates = get_submitted_dates(from_date, to_date, report_resource)

        assert submitted_dates == set()

    def test_get_submitted_dates_partial_overlap(self, report_resource):
        """Test get_submitted_dates when submission period partially overlaps query period"""
        from_date = dt('2025-6-1')
        to_date = dt('2025-6-5')

        # Create a submission that starts before our query period and ends during it
        TimesheetSubmissionFactory(
            resource=report_resource,
            period=(dt('2025-5-2'), dt('2025-6-3')),
        )

        submitted_dates = get_submitted_dates(from_date, to_date, report_resource)

        # Should only include dates within our query period that are also submitted
        expected_dates = {
            dt('2025-6-1'),
            dt('2025-6-2'),
        }

        assert submitted_dates == expected_dates

    def test_get_days_submission(self, report_resource):
        """Test get_days_submission returns correct submission status for each day"""
        from_date = dt('2025-5-30')
        to_date = dt('2025-6-5')

        TimesheetSubmissionFactory(
            resource=report_resource,
            period=(dt('2025-5-31'), dt('2025-6-3')),
        )

        days_submission = get_days_submission(from_date, to_date, report_resource)

        expected = {
            dt('2025-5-30'): False,
            dt('2025-5-31'): True,
            dt('2025-6-1'): True,
            dt('2025-6-2'): True,
            dt('2025-6-3'): False,
            dt('2025-6-4'): False,
            dt('2025-6-5'): False,
        }

        assert days_submission == expected
