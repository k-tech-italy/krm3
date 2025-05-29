import datetime
from contextlib import nullcontext as does_not_raise

import freezegun
import pytest
from django.core import exceptions

from testutils.factories import POFactory, ProjectFactory, TaskFactory


class TestProject:
    @freezegun.freeze_time(datetime.date(2024, 1, 1))
    @pytest.mark.parametrize(
        'end_date',
        (pytest.param(None, id='without_end_date'), pytest.param(datetime.date(2030, 1, 1), id='with_end_date')),
    )
    def test_generates_start_date(self, end_date):
        project = ProjectFactory(start_date=None, end_date=end_date)
        assert project.start_date == datetime.date.today()

    def test_accepts_missing_end_date(self):
        """Verify that date validation doesn't trigger if `end_date` is missing."""
        with does_not_raise():
            ProjectFactory(start_date=datetime.date(2024, 1, 1), end_date=None)

    def test_raises_when_ends_before_starting(self):
        with does_not_raise():
            # edge case: one day long project
            _valid = ProjectFactory(start_date=datetime.date(2024, 1, 1), end_date=datetime.date(2024, 1, 1))

        with pytest.raises(exceptions.ValidationError, match='must not be later'):
            _should_fail = ProjectFactory(start_date=datetime.date(2024, 1, 1), end_date=datetime.date(2020, 1, 1))


class TestPO:
    def test_accepts_missing_end_date(self):
        """Verify that date validation doesn't trigger if `end_date` is missing."""
        with does_not_raise():
            POFactory(start_date=datetime.date(2024, 1, 1), end_date=None)

    def test_raises_when_ends_before_starting(self):
        with does_not_raise():
            # edge case: one day long PO
            _valid = POFactory(start_date=datetime.date(2024, 1, 1), end_date=datetime.date(2024, 1, 1))

        with pytest.raises(exceptions.ValidationError, match='must not be later'):
            _should_fail = POFactory(start_date=datetime.date(2024, 1, 1), end_date=datetime.date(2020, 1, 1))


class TestTask:
    def test_raises_when_starting_before_related_project(self):
        project = ProjectFactory(start_date=datetime.date(2024, 1, 1))

        with does_not_raise():
            _valid_task_starting_on_same_day = TaskFactory(project=project, start_date=project.start_date)
            _valid_task_starting_later = TaskFactory(project=project, start_date=datetime.date(2025, 12, 31))

        # NOTE: this will keep the instance around for later checks
        with pytest.raises(exceptions.ValidationError) as excinfo:
            _invalid_task_starting_earlier = TaskFactory(
                title='Invalid', project=project, start_date=datetime.date(2020, 1, 1)
            )
        expected_message = (
            'A task must not start before its related project - '
            f'task "Invalid" is supposed to start on {datetime.date(2020, 1, 1).isoformat()}, '
            f'but related project "{project.name}" starts on {project.start_date.isoformat()}'
        )
        assert expected_message in excinfo.value.messages

    def test_accepts_missing_end_date(self):
        """Verify that date validation doesn't trigger if `end_date` is missing."""
        with does_not_raise():
            TaskFactory(start_date=datetime.date(2024, 1, 1), end_date=None)

    def test_raises_when_ends_before_starting(self):
        with does_not_raise():
            # edge case: one day long task
            _valid = TaskFactory(start_date=datetime.date(2024, 1, 1), end_date=datetime.date(2024, 1, 1))

        with pytest.raises(exceptions.ValidationError, match='must not be later'):
            _should_fail = TaskFactory(start_date=datetime.date(2024, 1, 1), end_date=datetime.date(2020, 1, 1))
