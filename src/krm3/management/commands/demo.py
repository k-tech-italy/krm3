import sys

from krm3.core.models import Resource

sys.path.append('tests/_extras')

import djclick as click

from testutils.factories import ResourceFactory, ProjectFactory, TaskFactory, UserFactory


@click.group()
def group():
    """Manages demo setup"""


def print_project(p) -> None:
    click.secho(f'- Project {p}', fg='yellow')
    for task in p.task_set.all():
        click.secho(f'  - Task {task} to {task.resource}', fg='yellow')



@group.command()
def timesheet() -> None:
    """Install Timesheet demo data."""
    projects = [
        ProjectFactory(name='Radiation protection practitioner'),
        ProjectFactory(name='Barrister'),
    ]
    users = [
        UserFactory(username='charles-sc', password='Pass1234'),  # noqa: S106
        UserFactory(username='keith-f', password='Pass1234')  # noqa: S106
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


def prepare_resources() -> list[Resource]:
    resources = list(Resource.objects.all())
    for _i in range(2 - len(resources)):
        resources.append(r := ResourceFactory())
        click.secho(f'Created resource {r}', fg='yellow')
    return resources
