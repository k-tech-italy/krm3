import pytest
from testutils.factories import (
    DayEntryFactory,
    ExpenseFactory,
    MissionFactory,
    ResourceFactory,
    TimesheetSubmissionFactory,
    UserFactory,
)
from testutils.permissions import add_permissions

from krm3.chat import services
from krm3.chat.registry import enabled_content_types
from krm3.core.models import TimesheetSubmission


@pytest.fixture(autouse=True)
def chat_enabled(settings):
    """The chat API is gated by CHAT_ENABLED (off by default)."""
    settings.FLAGS = {**settings.FLAGS, 'CHAT_ENABLED': [('boolean', True)]}


# label -> (factory building a record owned by `resource`, view permission, manage permission)
RECORD_BUILDERS = {
    'core.mission': (
        lambda resource: MissionFactory(resource=resource),
        'core.view_any_mission',
        'core.manage_any_mission',
    ),
    'core.expense': (
        lambda resource: ExpenseFactory(mission=MissionFactory(resource=resource)),
        'core.view_any_expense',
        'core.manage_any_expense',
    ),
    'core.dayentry': (
        lambda resource: DayEntryFactory(resource=resource),
        'core.view_any_timesheet',
        'core.manage_any_timesheet',
    ),
    'core.timesheetsubmission': (
        lambda resource: TimesheetSubmissionFactory(resource=resource, status=TimesheetSubmission.Status.DRAFT),
        'core.view_any_timesheet',
        'core.manage_any_timesheet',
    ),
}


@pytest.fixture
def record_builders():
    return RECORD_BUILDERS


@pytest.fixture
def owner(db):
    return UserFactory()


@pytest.fixture
def owner_resource(owner):
    return ResourceFactory(user=owner)


@pytest.fixture
def mission(owner_resource):
    return MissionFactory(resource=owner_resource)


@pytest.fixture
def mission_thread(owner, mission):
    content_type = enabled_content_types()['core.mission']
    thread, __ = services.resolve_record_thread(owner, mission, content_type)
    return thread


@pytest.fixture
def user_with_perms():
    def fx(*perms):
        user = UserFactory()
        if perms:
            add_permissions(user, list(perms))
        return user

    return fx
