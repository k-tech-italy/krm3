import pytest
from django.core.exceptions import ValidationError

from testutils.factories import DayEntryFactory, TaskEntryFactory, TaskFactory


@pytest.mark.django_db
def test_task_entry_rejects_task_assigned_to_another_resource():
    day_entry = DayEntryFactory()
    task = TaskFactory(contract=True)

    with pytest.raises(ValidationError, match='task is not assigned to the resource'):
        TaskEntryFactory(day_entry=day_entry, task=task)
