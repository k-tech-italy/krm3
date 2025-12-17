import datetime
from contextlib import nullcontext as does_not_raise

import freezegun
import pytest
from django.core import exceptions
from django.urls import reverse

from krm3.projects.forms import ProjectForm
from testutils.factories import POFactory, ProjectFactory, TaskFactory


class TestProjectForm:
    @freezegun.freeze_time(datetime.date(2025, 6, 15))
    def test_sets_start_date_default_to_today_on_new_instance(self):
        form = ProjectForm()
        assert form.fields['start_date'].initial == datetime.date(2025, 6, 15)

    def test_no_default_override_on_existing_instance(self):
        project = ProjectFactory(start_date=datetime.date(2020, 1, 1))
        form = ProjectForm(instance=project)
        assert form.fields['start_date'].initial is None

    def test_project_start_date_cannot_be_later_than_task_start_date(self,  krm3client, resource, admin_client):
        url = reverse('admin:core_project_add')
        data = {
            'name': 'Test Project',
            'start_date': '2020-01-01',
            'client': krm3client.id,
            'task_set-TOTAL_FORMS': 1,
            'task_set-INITIAL_FORMS': 0,
            'task_set-MIN_NUM_FORMS': 0,
            'task_set-MAX_NUM_FORMS': 1000,
            'task_set-0-title': 'Test Task',
            'task_set-0-work_price': 1,
            'task_set-0-start_date': '2019-01-01',
            'task_set-0-resource': resource.id
        }
        response = admin_client.post(url, data)
        formset = response.context['inline_admin_formsets'][0].formset
        assert 'A task must not start before its related project' in formset.errors[0]['__all__'][0]


class TestProject:
    @freezegun.freeze_time(datetime.date(2024, 1, 1))
    @pytest.mark.parametrize(
        'end_date',
        (pytest.param(None, id='without_end_date'), pytest.param(datetime.date(2030, 1, 1), id='with_end_date')),
    )
    def test_start_date_is_required(self, end_date):
        with pytest.raises(exceptions.ValidationError, match='is required'):
            _should_fail = ProjectFactory(start_date=None, end_date=end_date)

    def test_accepts_missing_end_date(self):
        """Verify that date validation doesn't trigger if `end_date` is missing."""
        with does_not_raise():
            ProjectFactory(start_date=datetime.date(2024, 1, 1), end_date=None)

    def test_raises_if_ends_before_starting(self):
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

    def test_raises_if_ends_before_starting(self):
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
        project = ProjectFactory(start_date=datetime.date(2024, 1, 1))
        with does_not_raise():
            TaskFactory(project=project, start_date=datetime.date(2024, 1, 1), end_date=None)

    def test_raises_if_ends_before_starting(self):
        project = ProjectFactory(start_date=datetime.date(2024, 1, 1))

        with does_not_raise():
            # edge case: one day long task
            _valid = TaskFactory(
                project=project, start_date=datetime.date(2024, 1, 1), end_date=datetime.date(2024, 1, 1)
            )

        with pytest.raises(exceptions.ValidationError, match='must not be later'):
            _should_fail = TaskFactory(
                project=project, start_date=datetime.date(2024, 1, 1), end_date=datetime.date(2020, 1, 1)
            )
