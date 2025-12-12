import datetime

import pytest
from django.urls import reverse
from freezegun import freeze_time

from krm3.timesheet.report.task import TimesheetTaskReportOnline
from tests._extras.testutils.factories import SuperUserFactory, TaskFactory, TimeEntryFactory, ContractFactory
from tests.unit.web.test_views import _assert_homepage_content


class TestTimesheetTaskReport:
    @pytest.fixture(autouse=True)
    def set_up_method(self):
        self.user = SuperUserFactory()

        contract_1 = ContractFactory()
        contract_2 = ContractFactory()

        self.r1 = contract_1.resource
        self.r2 = contract_2.resource

        self.task_1 = TaskFactory(
            start_date=datetime.date(2025, 6, 15), end_date=datetime.date(2025, 7, 30), resource=self.r1
        )

        self.task_2 = TaskFactory(
            start_date=datetime.date(2025, 6, 5), end_date=datetime.date(2025, 6, 10), resource=self.r1
        )

        self.task_3 = TaskFactory(
            start_date=datetime.date(2025, 6, 5), end_date=datetime.date(2025, 7, 10), resource=self.r2
        )

        TimeEntryFactory(
            date=datetime.date(2025, 6, 16),
            day_shift_hours=6,
            night_shift_hours=2,
            task=self.task_1,
            resource=self.r1,
        )
        TimeEntryFactory(
            date=datetime.date(2025, 6, 17),
            day_shift_hours=7,
            night_shift_hours=2,
            task=self.task_1,
            resource=self.r1,
        )
        TimeEntryFactory(
            date=datetime.date(2025, 6, 25), day_shift_hours=0, travel_hours=5, task=self.task_1, resource=self.r1
        )
        TimeEntryFactory(
            date=datetime.date(2025, 6, 22), day_shift_hours=0, on_call_hours=5, task=self.task_1, resource=self.r1
        )
        TimeEntryFactory(
            date=datetime.date(2025, 6, 22), day_shift_hours=0, on_call_hours=3, task=self.task_2, resource=self.r1
        )
        TimeEntryFactory(
            date=datetime.date(2025, 6, 23), day_shift_hours=0, on_call_hours=4, task=self.task_2, resource=self.r1
        )
        TimeEntryFactory(
            date=datetime.date(2025, 6, 17),
            day_shift_hours=5,
            night_shift_hours=3,
            task=self.task_2,
            resource=self.r1,
        )
        TimeEntryFactory(
            date=datetime.date(2025, 6, 18),
            day_shift_hours=0,
            holiday_hours=8,
            resource=self.r1,
        )
        TimeEntryFactory(
            date=datetime.date(2025, 6, 19),
            day_shift_hours=0,
            sick_hours=8,
            resource=self.r1,
        )
        TimeEntryFactory(date=datetime.date(2025, 6, 20), leave_hours=3, day_shift_hours=0, resource=self.r1)

        self.start_date = datetime.date(2025, 6, 1)
        self.end_date = datetime.date(2025, 6, 30)

    def test_header_data(self):
        """Test header row contains correct summary data."""
        report = TimesheetTaskReportOnline(self.start_date, self.end_date, self.user)
        blocks = report.report_html()

        matching_blocks = [b for b in blocks if b.resource and b.resource.pk == self.r1.id]
        resource1_block = matching_blocks[0]
        assert resource1_block is not None

        header_row = resource1_block.rows[0]
        working_days = header_row.cells[0].render()
        assert working_days == '20'

        total_hours = header_row.cells[1].render()
        assert total_hours == '160'

    def test_task_rows_exist(self):
        """Test that task rows are created for resources with tasks."""
        report = TimesheetTaskReportOnline(self.start_date, self.end_date, self.user)
        blocks = report.report_html()

        matching_blocks = [b for b in blocks if b.resource and b.resource.pk == self.r1.id]
        resource1_block = matching_blocks[0]
        assert resource1_block is not None

        def has_expected_task_title(row):
            return row.cells[0].render() == str(self.task_1)

        assert any(has_expected_task_title(row) for row in resource1_block.rows[1:])

    def test_task_hours_calculation(self):
        """Test that task hours are calculated correctly."""
        report = TimesheetTaskReportOnline(self.start_date, self.end_date, self.user)
        blocks = report.report_html()

        matching_blocks = [b for b in blocks if b.resource and b.resource.pk == self.r1.id]
        resource1_block = matching_blocks[0]
        assert resource1_block is not None

        task1_row = None
        for row in resource1_block.rows[1:]:
            if row.cells[0].render() == str(self.task_1):
                task1_row = row
                break

        assert task1_row is not None

        total_hours_cell = task1_row.cells[2].render()
        assert total_hours_cell == '22'

    def test_tot_per_giorno_row(self):
        """Test that 'Tot per Giorno' row sums task hours correctly."""
        report = TimesheetTaskReportOnline(self.start_date, self.end_date, self.user)
        blocks = report.report_html()

        matching_blocks = [b for b in blocks if b.resource and b.resource.pk == self.r1.id]
        resource1_block = matching_blocks[0]
        assert resource1_block is not None

        tot_row = None
        for row in resource1_block.rows:
            if row.cells[0].render() == 'Total per day':
                tot_row = row
                break

        assert tot_row is not None

        total_hours_cell = tot_row.cells[2].render()
        assert total_hours_cell == '30'

    def test_absence_row(self):
        """Test that absence row exists and shows correct markers."""
        report = TimesheetTaskReportOnline(self.start_date, self.end_date, self.user)
        blocks = report.report_html()

        matching_blocks = [b for b in blocks if b.resource and b.resource.pk == self.r1.id]
        resource1_block = matching_blocks[0]
        assert resource1_block is not None

        absence_row = None
        for row in resource1_block.rows:
            if row.cells[0].render() == 'Absences':
                absence_row = row
                break

        assert absence_row is not None
        assert absence_row.cells[20].render() == 'F'
        assert absence_row.cells[21].render() == 'M'
        assert absence_row.cells[22].render() == 'L'


# View tests for task report


@freeze_time('2025-08-22')
def test_task_report_view_current_month(client):
    SuperUserFactory(username='user00', password='pass123')
    task = TaskFactory()
    TimeEntryFactory(resource=task.resource, day_shift_hours=8, date=datetime.date.today(), task=task)
    client.login(username='user00', password='pass123')
    url = reverse('task_report')
    response = client.get(url)
    _assert_homepage_content(response)
    assert response.status_code == 200
    content = response.content.decode()
    assert '<h1 class="title">Task Report August 2025</h1>' in content


@freeze_time('2025-08-22')
@pytest.mark.parametrize(
    'month, expected_result',
    [
        pytest.param('202509', 'Task Report September 2025', id='next_month'),
        pytest.param('202507', 'Task Report July 2025', id='previous_month'),
    ],
)
def test_task_report_view_next_previous_month(client, month, expected_result):
    SuperUserFactory(username='user00', password='pass123')
    client.login(username='user00', password='pass123')
    response = client.get(reverse('task-report-month', args=[month]))
    _assert_homepage_content(response)
    assert response.status_code == 200
    assert expected_result in response.content.decode()
