import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from testutils.factories import (
    ChatMessageFactory,
    ChatThreadFactory,
    DayEntryFactory,
    DirectChatThreadFactory,
    ExpenseFactory,
    MissionFactory,
    ResourceFactory,
    TaskEntryFactory,
    TimesheetSubmissionFactory,
    UserFactory,
)

from krm3.config.fragments.constance import chat_content_types_validation
from krm3.core.models import ChatMessage, ChatParticipant, ChatThread, Mission, TimesheetSubmission


def _thread_with_messages(record):
    thread = ChatThreadFactory(content_object=record)
    ChatMessageFactory(thread=thread)
    ChatParticipant.objects.create(thread=thread, user=UserFactory())
    return thread


def test_deleting_record_removes_thread():
    mission = MissionFactory()
    _thread_with_messages(mission)

    mission.delete()

    assert not ChatThread.objects.exists()
    assert not ChatMessage.objects.exists()
    assert not ChatParticipant.objects.exists()


def test_fk_cascade_removes_child_threads():
    expense = ExpenseFactory()
    _thread_with_messages(expense)
    _thread_with_messages(expense.mission)

    Mission.objects.filter(pk=expense.mission.pk).delete()

    assert not ChatThread.objects.exists()


def test_day_entry_cascade_removes_task_entry_threads():
    task_entry = TaskEntryFactory(day_entry=True)
    _thread_with_messages(task_entry)
    _thread_with_messages(task_entry.day_entry)

    task_entry.day_entry.delete()

    assert not ChatThread.objects.exists()


def test_deleting_record_keeps_other_threads():
    keep = _thread_with_messages(MissionFactory())
    dm = DirectChatThreadFactory()
    DayEntryFactory()

    MissionFactory().delete()

    assert set(ChatThread.objects.values_list('pk', flat=True)) == {keep.pk, dm.pk}


def test_one_thread_per_record():
    mission = MissionFactory()
    ChatThreadFactory(content_object=mission)

    with pytest.raises(IntegrityError):
        ChatThreadFactory(content_object=mission)


def test_one_direct_thread_per_pair():
    alice, bob = UserFactory(), UserFactory()
    DirectChatThreadFactory(users=(alice, bob))

    with pytest.raises(IntegrityError):
        DirectChatThreadFactory(users=(bob, alice))


@pytest.mark.parametrize(
    'fields',
    [
        pytest.param({'kind': 'DIRECT'}, id='direct-without-users'),
        pytest.param({'kind': 'RECORD'}, id='record-without-target'),
    ],
)
def test_kind_fields_constraint(fields):
    with pytest.raises(IntegrityError):
        ChatThread.objects.create(created_by=UserFactory(), **fields)


def test_direct_users_must_be_ordered_and_distinct():
    alice, bob = sorted((UserFactory(), UserFactory()), key=lambda u: u.pk)

    with pytest.raises(IntegrityError):
        ChatThread.objects.create(kind='DIRECT', direct_user_low=bob, direct_user_high=alice, created_by=alice)


def test_users_with_chat_history_cannot_be_deleted():
    from django.db.models import ProtectedError  # noqa: PLC0415

    message = ChatMessageFactory()

    with pytest.raises(ProtectedError):
        message.author.delete()


def test_message_str_does_not_leak_body():
    message = ChatMessageFactory(body='top secret')

    assert 'top secret' not in str(message)


@pytest.mark.parametrize(
    'value',
    [
        pytest.param('core.mission', id='single'),
        pytest.param(' core.Mission , core.taskentry ', id='spaces-and-case'),
        pytest.param('', id='empty'),
    ],
)
def test_constance_validator_accepts(value):
    chat_content_types_validation(value)


@pytest.mark.parametrize(
    'value',
    [
        pytest.param('core.project', id='not-chat-capable'),
        pytest.param('core.mission,core.nope', id='unknown'),
        pytest.param('mission', id='malformed'),
    ],
)
def test_constance_validator_rejects(value):
    with pytest.raises(ValidationError):
        chat_content_types_validation(value)


@pytest.mark.parametrize(
    ('perm', 'sees_all'),
    [
        pytest.param(None, False, id='regular'),
        pytest.param('core.view_any_timesheet', True, id='view-only'),
        pytest.param('core.manage_any_timesheet', True, id='manager'),
    ],
)
def test_timesheet_submission_filter_acl(user_with_perms, perm, sees_all):
    user = user_with_perms(*([perm] if perm else []))
    own = TimesheetSubmissionFactory(resource=ResourceFactory(user=user), closed=False)
    other = TimesheetSubmissionFactory(resource=ResourceFactory(), closed=False)

    visible = set(TimesheetSubmission.objects.filter_acl(user))

    assert visible == ({own, other} if sees_all else {own})


def test_timesheet_submission_filter_acl_superuser(admin_user):
    submissions = {TimesheetSubmissionFactory(closed=False), TimesheetSubmissionFactory(closed=False)}

    assert set(TimesheetSubmission.objects.filter_acl(admin_user)) == submissions
