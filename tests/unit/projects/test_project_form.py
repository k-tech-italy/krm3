import freezegun
from django.urls import reverse
from ktcalendars.utils import dt
from testutils.factories import ProjectFactory

from krm3.projects.forms import ProjectForm

@freezegun.freeze_time(dt('2025-06-15'))
def test_sets_start_date_default_to_today_on_new_instance():
    form = ProjectForm()
    assert form.fields['period'].initial == (dt('2025-06-15'), None)


def test_no_default_override_on_existing_instance():
    project = ProjectFactory(period=(dt('2020-01-01'), None))
    form = ProjectForm(instance=project)
    assert form.fields['period'].initial is None
