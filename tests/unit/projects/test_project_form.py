import freezegun
from django.urls import reverse

from krm3.projects.forms import ProjectForm
from testutils.date_utils import _dt
from testutils.factories import ProjectFactory


@freezegun.freeze_time(_dt('2025-06-15'))
def test_sets_start_date_default_to_today_on_new_instance():
    form = ProjectForm()
    assert form.fields['period'].initial == (_dt('2025-06-15'), None)


def test_no_default_override_on_existing_instance():
    project = ProjectFactory(period=(_dt('2020-01-01'), None))
    form = ProjectForm(instance=project)
    assert form.fields['period'].initial is None


def test_project_start_date_cannot_be_later_than_task_start_date(krm3client, resource, admin_client):
    url = reverse('admin:core_project_add')
    data = {
        'name': 'Test Project',
        'period_0': '2020-01-01',
        'client': krm3client.id,
        'task_set-TOTAL_FORMS': 1,
        'task_set-INITIAL_FORMS': 0,
        'task_set-MIN_NUM_FORMS': 0,
        'task_set-MAX_NUM_FORMS': 1000,
        'task_set-0-title': 'Test Task',
        'task_set-0-work_price': 1,
        'task_set-0-period_0': '2019-01-01',
        'task_set-0-resource': resource.id,
    }
    response = admin_client.post(url, data)
    formset = response.context['inline_admin_formsets'][0].formset
    assert 'Missing contract cover for the range [2019-01-01:...)' in formset.errors[0]['__all__'][0]
