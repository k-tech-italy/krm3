"""
Hint: keep the file ./test_timesheet_report.xlsx aligned with fixture report_resource
"""

import pathlib
from decimal import Decimal as D

import pytest

from krm3.timesheet.report import timesheet_report_raw_data, calculate_overtime
from krm3.utils.dates import dt
from testutils import yaml as test_yaml
from testutils.factories import TimeEntryFactory, TaskFactory, SpecialLeaveReasonFactory


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
        # TimeEntryFactory(resource=r1, date='2025-06-03', day_shift_hours=0, rest_hours=3),
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
        'special_leave|1': [D('0.00'), D('0.00'), D('0.00'), D('0.00'), D('0.00'), D('0.00'), D('0.50'), D('0.00')],
        'special_leave|2': [D('0.00'), D('0.00'), D('0.00'), D('0.00'), D('0.00'), D('0.00'), D('0.00'), D('5.0')],
        'sick': [D('0.00'), D('0.00'), D('8.00'), D('0.00'), D('0.00'), D('0.00'), D('0.00'), D('0.00')],
        'overtime': [D('0.00'), D('0.00'), D('0.00'), D('0.00'), D('0.00'), D('0.00'), D('0.00'), D('0.00')],
    }


class TestTimesheetReport:
    # @pytest.mark.parametrize(
    #     ('data', 'expected'), test_yaml.generate_parameters(pathlib.Path(__file__).parent / 'testcases/timesheet_report')
    # )
    # def test_report_daysum(self, data, expected):
    #     # test logic goes here
    #     print(data, expected)
    #     # TODO
    #     assert False

    def test_report_raw_data(self, report_resource):
        from krm3.core.models import TimeEntry

        assert TimeEntry.objects.count() == report_resource._time_entries.__len__()
        result = timesheet_report_raw_data(dt('2025-05-30'), dt('2025-06-06'))
        assert result == {report_resource: _raw_results()}

    # def test_calculate_overtime(self):
    #     results = calculate_overtime({"<resource>": _raw_results()})
    #     # TODO
    #     assert False
