import datetime
from contextlib import nullcontext as does_not_raise

import pytest
from django.core import exceptions

from testutils.factories import ProjectFactory, TaskFactory


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
        assert excinfo.value.message == expected_message
