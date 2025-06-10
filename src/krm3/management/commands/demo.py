import random
import sys
import typing


from krm3.core.models import Resource, TimeEntry
from krm3.utils.dates import KrmDay, KrmCalendar

sys.path.append('tests/_extras')

import djclick as click

if typing.TYPE_CHECKING:
    from krm3.core.models import Project

from testutils.factories import ResourceFactory, ProjectFactory, TaskFactory, UserFactory


@click.group()
def group() -> None:
    """Manage demo setup."""


def print_project(p: 'Project') -> None:
    click.secho(f'- Project {p}', fg='yellow')
    for task in p.task_set.all():
        click.secho(f'  - Task {task} to {task.resource}', fg='yellow')


@group.command()
def timesheet() -> None:  # noqa: PLR0912, C901
    """Install Timesheet demo data."""
    projects = [
        ProjectFactory(name='Radiation protection practitioner'),
        ProjectFactory(name='Barrister'),
    ]
    users = [
        UserFactory(username='charles-sc', password='Pass1234'),  # noqa: S106
        UserFactory(username='keith-f', password='Pass1234'),  # noqa: S106
    ]
    resources = [
        ResourceFactory(first_name='Charles', last_name='Santa Cruz do Nascimiento', user=users[0]),
        ResourceFactory(first_name='Keith', last_name='Fuller', user=users[1]),
    ]
    tasks = [
        TaskFactory(title='Bake pie', project=projects[0], resource=resources[0]),
        TaskFactory(title='Build wall', project=projects[0], resource=resources[0]),
        TaskFactory(title='Change sink', project=projects[0], resource=resources[0]),
        TaskFactory(title='Fix shower', project=projects[0], resource=resources[1]),
        TaskFactory(title='Repair rear car bumper', project=projects[1], resource=resources[1]),
    ]

    click.secho('Found or created following records:', fg='yellow')
    for p in projects:
        print_project(p)

    # Reset all time entries for resources
    TimeEntry.objects.filter(resource__in=resources).delete()

    today = KrmDay()
    for i in range(12):
        for day in KrmCalendar().iter_week(today - 7 * i):
            match i:
                case 0:  # Sick
                    if not day.is_holiday:
                        TimeEntry.objects.create(
                            resource=resources[0], date=day.date, day_shift_hours=0, sick_hours=8, comment='Feel sick'
                        )
                case 1:
                    if not day.is_holiday:  # Holiday
                        TimeEntry.objects.create(
                            resource=resources[0], date=day.date, day_shift_hours=0, holiday_hours=8
                        )
                case 2 | 3:
                    if not day.is_holiday:  # Regular hours
                        TimeEntry.objects.create(
                            resource=resources[0],
                            date=day.date,
                            task=random.choice(tasks[:3]),  # noqa: S311
                            day_shift_hours=8,
                        )
                case 4:
                    if not day.is_holiday:  # Split on tasks
                        task_set = tasks[:3]
                        random.shuffle(task_set)
                        t1, t2 = task_set[:2]
                        TimeEntry.objects.create(resource=resources[0], date=day.date, task=t1, day_shift_hours=6)
                        TimeEntry.objects.create(resource=resources[0], date=day.date, task=t2, day_shift_hours=2)
                case 5, 6, 7:
                    if not day.is_holiday:  # full on tasks
                        TimeEntry.objects.create(
                            resource=resources[0], date=day.date, task=tasks[i % 3], day_shift_hours=8
                        )
                case 8, 9, 10, 11, 12:
                    if not day.is_holiday:  # full on tasks
                        TimeEntry.objects.create(
                            resource=resources[0],
                            date=day.date,
                            task=tasks[i % 3],
                            day_shift_hours=8,
                            night_shift_hours=4,
                        )
                        TimeEntry.objects.create(
                            resource=resources[0], date=day.date, day_shift_hours=0, leave_hours=i % 3 + 0.5
                        )
    click.secho(f'Created {TimeEntry.objects.filter(resource=resources[0]).count()} time entries.', fg='green')

def prepare_resources() -> list[Resource]:
    resources = list(Resource.objects.all())
    for _i in range(2 - len(resources)):
        resources.append(r := ResourceFactory())
        click.secho(f'Created resource {r}', fg='yellow')
    return resources
