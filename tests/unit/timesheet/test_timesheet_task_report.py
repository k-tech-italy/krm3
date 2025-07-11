import datetime
import pytest

from krm3.timesheet.task_report import timesheet_task_report_raw_data
from testutils.factories import TimeEntryFactory, TaskFactory

class TestTimesheetTaskReportRawData:

    @pytest.fixture(autouse=True)
    def set_up_method(self):
        task_1 = TaskFactory(start_date=datetime.date(2025, 6, 15),
                             end_date=datetime.date(2025, 7, 30))

        task_2 = TaskFactory(start_date=datetime.date(2025, 6, 5),
                             end_date=datetime.date(2025, 6, 10),
                             resource=task_1.resource)

        # task for different user
        task_3 = TaskFactory(start_date=datetime.date(2025, 6, 5), end_date=datetime.date(2025, 7, 10))

        TimeEntryFactory(
            date=datetime.date(2025, 6, 16),
            day_shift_hours=6,
            night_shift_hours=2,
            task=task_1,
            resource=task_1.resource
        )
        TimeEntryFactory(
            date=datetime.date(2025, 6, 17),
            day_shift_hours=7,
            night_shift_hours=2,
            task=task_1,
            resource=task_1.resource
        )
        TimeEntryFactory(
            date=datetime.date(2025, 6, 25),
            day_shift_hours=0,
            travel_hours=5,
            task=task_1,
            resource=task_1.resource
        )
        TimeEntryFactory(
            date=datetime.date(2025, 6, 22),
            day_shift_hours=0,
            on_call_hours=5,
            task=task_1,
            resource=task_1.resource
        )
        TimeEntryFactory(
            date=datetime.date(2025, 6, 22),
            day_shift_hours=0,
            on_call_hours=3,
            task=task_2,
            resource=task_2.resource
        )
        TimeEntryFactory(
            date=datetime.date(2025, 6, 23),
            day_shift_hours=0,
            on_call_hours=4,
            task=task_2,
            resource=task_2.resource
        )
        TimeEntryFactory(
            date=datetime.date(2025, 6, 17),
            day_shift_hours=5,
            night_shift_hours=3,
            task=task_2,
            resource=task_1.resource
        )
        TimeEntryFactory(
            date=datetime.date(2025, 6, 18),
            day_shift_hours=0,
            holiday_hours=8,
            resource=task_1.resource,
        )
        TimeEntryFactory(
            date=datetime.date(2025, 6, 19),
            day_shift_hours=0,
            sick_hours=8,
            resource=task_1.resource,
        )
        TimeEntryFactory(
            date=datetime.date(2025, 6, 20),
            leave_hours=3,
            day_shift_hours=0,
            resource=task_1.resource
        )
        start = datetime.date(2025, 6, 1)
        end = datetime.date(2025, 6, 30)

        data = timesheet_task_report_raw_data(start, end)
        self.data = {'task_1': task_1, 'task_2': task_2, 'task_3': task_3, 'data': data}

    def test_header_data(self):
        data = self.data['data']
        task_1 = self.data['task_1']

        assert data[task_1.resource]['NUM GIORNI'] == 15
        assert data[task_1.resource]['TOT HH'] == 120

    def test_task_data(self):
        data = self.data['data']
        task_1 = self.data['task_1']
        task_2 = self.data['task_2']

        assert data[task_1.resource][task_1][0] == 22 / 8
        assert data[task_1.resource][task_1][1] == 22
        assert data[task_1.resource][task_1][17] == 8
        assert data[task_1.resource][task_1][18] == 9
        assert data[task_1.resource][task_1][26] == 5

        assert data[task_2.resource][task_2][0] == 1
        assert data[task_2.resource][task_2][1] == 8
        assert data[task_2.resource][task_2][18] == 8

    def test_tot_per_giorno_data(self):
        data = self.data['data']
        task_1 = self.data['task_1']

        assert data[task_1.resource]['Tot per Giorno'][0] == 30 / 8
        assert data[task_1.resource]['Tot per Giorno'][1] == 30
        assert data[task_1.resource]['Tot per Giorno'][17] == 8
        assert data[task_1.resource]['Tot per Giorno'][18] == 17
        assert data[task_1.resource]['Tot per Giorno'][26] == 5

    def test_notturni_data(self):
        data = self.data['data']
        task_1 = self.data['task_1']
        assert data[task_1.resource]['Notturni'][0] == 7 / 8
        assert data[task_1.resource]['Notturni'][1] == 7
        assert data[task_1.resource]['Notturni'][17] == 2
        assert data[task_1.resource]['Notturni'][18] == 5

    def test_reperibilita_data(self):
        data = self.data['data']
        task_1 = self.data['task_1']
        assert data[task_1.resource]['Reperibilità'][0] == 12 / 8
        assert data[task_1.resource]['Reperibilità'][1] == 12
        assert data[task_1.resource]['Reperibilità'][23] == 8
        assert data[task_1.resource]['Reperibilità'][24] == 4

    def test_ore_trasferta_data(self):
        data = self.data['data']
        task_1 = self.data['task_1']

        assert data[task_1.resource]['Ore Trasferta'][0] == 5 / 8
        assert data[task_1.resource]['Ore Trasferta'][1] == 5
        assert data[task_1.resource]['Ore Trasferta'][26] == 5

    def test_assenze_data(self):
        data = self.data['data']
        task_1 = self.data['task_1']

        assert data[task_1.resource]['Assenze'][0] == 19 / 8
        assert data[task_1.resource]['Assenze'][1] == 19
        assert data[task_1.resource]['Assenze'][19] == 'F'
        assert data[task_1.resource]['Assenze'][20] == 'M'
        assert data[task_1.resource]['Assenze'][21] == 3

    def test_no_entries_table(self):
        data = self.data['data']
        task_3 = self.data['task_3']

        assert data[task_3.resource]['NUM GIORNI'] == 18
        assert data[task_3.resource]['TOT HH'] == 144

        table_rows = [row for label, row in data[task_3.resource].items() if label not in ['NUM GIORNI', 'TOT HH']]

        for row in table_rows:
            for cell in row:
                assert cell == 0

    def test_data_for_one_resource(self):
        task_1 = self.data['task_1']
        task_2 = self.data['task_2']

        start = datetime.date(2025, 6, 1)
        end = datetime.date(2025, 6, 30)

        data = timesheet_task_report_raw_data(start, end, task_1.resource)

        assert len(data.keys()) == 1
        assert data[task_1.resource]['NUM GIORNI'] == 15
        assert data[task_1.resource]['TOT HH'] == 120
        assert data[task_1.resource][task_1][26] == 5
        assert data[task_2.resource][task_2][18] == 8
