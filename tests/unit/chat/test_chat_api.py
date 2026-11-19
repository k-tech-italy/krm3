import datetime

import pytest
from constance.test import override_config
from django.utils import timezone
from freezegun import freeze_time
from rest_framework.reverse import reverse
from testutils.factories import (
    ChatMessageFactory,
    DirectChatThreadFactory,
    MissionFactory,
    ResourceFactory,
    UserFactory,
)

from krm3.chat import services
from krm3.core.models import ChatParticipant, ChatThread

RESOLVE = 'chat-api:thread-resolve-record'


def messages_url(thread):
    return reverse('chat-api:thread-messages', args=[thread.pk])


# --- record threads -------------------------------------------------------------------------------------------


def test_resolve_record_reuses_the_thread(api_client, owner, mission, user_with_perms):
    payload = {'contentType': 'core.mission', 'objectId': mission.pk}
    manager = user_with_perms('core.manage_any_mission')

    first = api_client(user=owner).post(reverse(RESOLVE), payload, format='json')
    second = api_client(user=manager).post(reverse(RESOLVE), payload, format='json')

    assert (first.status_code, second.status_code) == (201, 200)
    assert first.json()['id'] == second.json()['id']
    assert ChatThread.objects.count() == 1


def test_resolve_record_adds_owner_and_requester(api_client, owner, mission, user_with_perms):
    manager = user_with_perms('core.manage_any_mission')

    response = api_client(user=manager).post(
        reverse(RESOLVE), {'contentType': 'core.mission', 'objectId': mission.pk}, format='json'
    )

    participants = ChatParticipant.objects.filter(thread_id=response.json()['id']).values_list('user', flat=True)
    assert set(participants) == {owner.pk, manager.pk}


def test_resolve_record_payload(api_client, owner, mission):
    response = api_client(user=owner).post(
        reverse(RESOLVE), {'contentType': 'core.mission', 'objectId': mission.pk}, format='json'
    )

    data = response.json()
    assert data['kind'] == 'RECORD'
    assert data['contentType'] == 'core.mission'
    assert data['objectId'] == mission.pk
    assert data['recordLabel'] == str(mission)
    assert data['otherUser'] is None
    assert data['unreadCount'] == 0


@pytest.mark.parametrize(
    'content_type',
    [
        pytest.param('core.project', id='not-chat-capable'),
        pytest.param('core.nonexistent', id='unknown'),
        pytest.param('mission', id='malformed'),
    ],
)
def test_resolve_record_rejects_content_type(api_client, owner, content_type):
    response = api_client(user=owner).post(
        reverse(RESOLVE), {'contentType': content_type, 'objectId': 1}, format='json'
    )

    assert response.status_code == 400


def test_resolve_record_unknown_object_is_404(api_client, admin_user):
    response = api_client(user=admin_user).post(
        reverse(RESOLVE), {'contentType': 'core.mission', 'objectId': 999999}, format='json'
    )

    assert response.status_code == 404


def test_disabled_type_hides_but_keeps_threads(api_client, owner, mission, mission_thread):
    ChatMessageFactory(thread=mission_thread, author=UserFactory())
    client = api_client(user=owner)
    payload = {'contentType': 'core.mission', 'objectId': mission.pk}

    with override_config(CHAT_RECORD_CONTENT_TYPES='core.expense'):
        assert client.post(reverse(RESOLVE), payload, format='json').status_code == 400
        assert client.get(messages_url(mission_thread)).status_code == 404
        assert client.get(reverse('chat-api:thread-list')).json()['count'] == 0
        assert client.get(reverse('chat-api:unread')).json()['total'] == 0

    assert ChatThread.objects.filter(pk=mission_thread.pk).exists()
    assert client.get(messages_url(mission_thread)).status_code == 200
    assert client.get(reverse('chat-api:unread')).json()['total'] == 1


def test_posting_allowed_on_closed_records(api_client, owner, owner_resource):
    mission = MissionFactory(resource=owner_resource, status='CANCELLED')
    thread = api_client(user=owner).post(
        reverse(RESOLVE), {'contentType': 'core.mission', 'objectId': mission.pk}, format='json'
    )

    response = api_client(user=owner).post(
        reverse('chat-api:thread-messages', args=[thread.json()['id']]), {'body': 'hi'}, format='json'
    )

    assert response.status_code == 201


# --- direct threads -------------------------------------------------------------------------------------------


def test_direct_thread_is_idempotent_per_pair(api_client):
    alice, bob = UserFactory(), UserFactory()

    first = api_client(user=alice).post(reverse('chat-api:thread-list'), {'userId': bob.pk}, format='json')
    second = api_client(user=bob).post(reverse('chat-api:thread-list'), {'userId': alice.pk}, format='json')

    assert (first.status_code, second.status_code) == (201, 200)
    assert first.json()['id'] == second.json()['id']
    assert first.json()['otherUser']['id'] == bob.pk
    assert second.json()['otherUser']['id'] == alice.pk
    thread = ChatThread.objects.get()
    assert set(thread.participants.values_list('user', flat=True)) == {alice.pk, bob.pk}


@pytest.mark.parametrize(
    'target',
    [
        pytest.param('self', id='self'),
        pytest.param('inactive', id='inactive'),
        pytest.param('missing', id='nonexistent'),
    ],
)
def test_direct_thread_invalid_target(api_client, target):
    alice = UserFactory()
    user_id = {
        'self': lambda: alice.pk,
        'inactive': lambda: UserFactory(is_active=False).pk,
        'missing': lambda: 999999,
    }[target]()

    response = api_client(user=alice).post(reverse('chat-api:thread-list'), {'userId': user_id}, format='json')

    assert response.status_code == 400


def test_superuser_cannot_read_others_dms(api_client, admin_user):
    thread = DirectChatThreadFactory()
    ChatMessageFactory(thread=thread, author=thread.direct_user_low, body='secret')
    client = api_client(user=admin_user)

    assert client.get(reverse('chat-api:thread-detail', args=[thread.pk])).status_code == 404
    assert client.get(messages_url(thread)).status_code == 404
    assert client.post(messages_url(thread), {'body': 'x'}, format='json').status_code == 404
    assert client.post(reverse('chat-api:thread-read', args=[thread.pk])).status_code == 404


def test_cannot_post_to_inactive_dm_partner(api_client):
    alice, bob = UserFactory(), UserFactory()
    thread, __ = services.get_or_create_direct_thread(alice, bob)
    ChatMessageFactory(thread=thread, author=bob)
    bob.is_active = False
    bob.save()
    client = api_client(user=alice)

    assert client.get(messages_url(thread)).status_code == 200
    assert client.post(messages_url(thread), {'body': 'hi'}, format='json').status_code == 400


# --- messages -------------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    'body',
    [
        pytest.param('', id='empty'),
        pytest.param('   ', id='blank'),
        pytest.param('x' * 4001, id='too-long'),
    ],
)
def test_message_body_validation(api_client, owner, mission_thread, body):
    response = api_client(user=owner).post(messages_url(mission_thread), {'body': body}, format='json')

    assert response.status_code == 400


def test_post_message_updates_thread_and_joins_author(api_client, mission_thread, user_with_perms):
    viewer = user_with_perms('core.view_any_mission')

    response = api_client(user=viewer).post(messages_url(mission_thread), {'body': '  hello  '}, format='json')

    assert response.status_code == 201
    assert response.json()['body'] == 'hello'
    mission_thread.refresh_from_db()
    assert mission_thread.last_message_at is not None
    assert mission_thread.participants.filter(user=viewer).exists()


def test_messages_are_cursor_paginated_newest_first(api_client, owner, mission_thread):
    for i in range(5):
        with freeze_time(timezone.now() + datetime.timedelta(minutes=i)):
            services.post_message(owner, mission_thread, f'msg {i}')
    client = api_client(user=owner)

    first = client.get(messages_url(mission_thread), {'page_size': 3}).json()
    second = client.get(first['next']).json()

    assert [m['body'] for m in first['results']] == ['msg 4', 'msg 3', 'msg 2']
    assert [m['body'] for m in second['results']] == ['msg 1', 'msg 0']
    assert second['next'] is None


def test_only_author_can_soft_delete(api_client, owner, mission_thread, user_with_perms):
    manager = user_with_perms('core.manage_any_mission')
    message = services.post_message(owner, mission_thread, 'oops')
    url = reverse('chat-api:message-detail', args=[message.pk])

    assert api_client(user=manager).delete(url).status_code == 403
    assert api_client(user=UserFactory()).delete(url).status_code == 404
    assert api_client(user=owner).delete(url).status_code == 204
    assert api_client(user=owner).delete(url).status_code == 204  # idempotent

    message.refresh_from_db()
    assert message.deleted_by == owner


def test_deleted_messages_are_placeholders(api_client, owner, mission_thread):
    message = services.post_message(owner, mission_thread, 'oops')
    services.soft_delete_message(owner, message)

    [result] = api_client(user=owner).get(messages_url(mission_thread)).json()['results']

    assert result['body'] is None
    assert result['isDeleted'] is True
    assert result['deletedAt'] is not None


# --- inbox and unread -----------------------------------------------------------------------------------------


def test_inbox_lists_participated_and_accessible_threads(api_client, owner, mission_thread, user_with_perms):
    manager = user_with_perms('core.manage_any_mission')
    # owner participates in a thread on someone else's mission, but can no longer access the record
    services.resolve_record_thread(
        owner, MissionFactory(resource=ResourceFactory(user=UserFactory())), mission_thread.content_type
    )

    owner_inbox = api_client(user=owner).get(reverse('chat-api:thread-list')).json()
    manager_inbox = api_client(user=manager).get(reverse('chat-api:thread-list')).json()

    assert [t['id'] for t in owner_inbox['results']] == [mission_thread.pk]
    assert manager_inbox['count'] == 0  # can access, but not a participant


def test_inbox_order_and_last_message(api_client, owner, mission_thread):
    bob = UserFactory()
    dm, __ = services.get_or_create_direct_thread(owner, bob)
    with freeze_time(timezone.now() + datetime.timedelta(minutes=1)):
        services.post_message(owner, mission_thread, 'older')
    with freeze_time(timezone.now() + datetime.timedelta(minutes=2)):
        services.post_message(bob, dm, 'x' * 500)

    results = api_client(user=owner).get(reverse('chat-api:thread-list')).json()['results']

    assert [t['id'] for t in results] == [dm.pk, mission_thread.pk]
    assert results[0]['lastMessage']['author']['id'] == bob.pk
    assert len(results[0]['lastMessage']['body']) == 140
    assert results[1]['lastMessage']['body'] == 'older'


def test_unread_counts(api_client, owner, mission_thread):
    bob = UserFactory()
    dm, __ = services.get_or_create_direct_thread(owner, bob)
    services.post_message(bob, dm, 'one')
    services.post_message(bob, dm, 'two')
    services.post_message(owner, dm, 'own message, not unread')
    deleted = services.post_message(bob, dm, 'deleted, not unread')
    services.soft_delete_message(bob, deleted)
    services.post_message(bob, mission_thread, 'not a participant yet')  # bob joins, owner is participant
    client = api_client(user=owner)

    unread = client.get(reverse('chat-api:unread')).json()

    assert unread['total'] == 3
    assert {(t['threadId'], t['count']) for t in unread['threads']} == {(dm.pk, 2), (mission_thread.pk, 1)}

    with freeze_time(timezone.now() + datetime.timedelta(seconds=1)):
        assert client.post(reverse('chat-api:thread-read', args=[dm.pk])).status_code == 200
    with freeze_time(timezone.now() + datetime.timedelta(seconds=2)):
        services.post_message(bob, dm, 'after read')

    unread = client.get(reverse('chat-api:unread')).json()
    assert {(t['threadId'], t['count']) for t in unread['threads']} == {(dm.pk, 1), (mission_thread.pk, 1)}


# --- feature flag and config ----------------------------------------------------------------------------------


@pytest.fixture
def chat_disabled(settings):
    settings.FLAGS = {**settings.FLAGS, 'CHAT_ENABLED': [('boolean', False)]}


def test_all_endpoints_forbidden_when_flag_disabled(api_client, owner, mission, mission_thread, chat_disabled):
    message = services.post_message(owner, mission_thread, 'hi')
    client = api_client(user=owner)
    pk = mission_thread.pk

    responses = [
        client.get(reverse('chat-api:thread-list')),
        client.post(reverse('chat-api:thread-list'), {'userId': UserFactory().pk}, format='json'),
        client.get(reverse('chat-api:thread-detail', args=[pk])),
        client.get(reverse('chat-api:thread-messages', args=[pk])),
        client.post(reverse('chat-api:thread-messages', args=[pk]), {'body': 'x'}, format='json'),
        client.post(reverse('chat-api:thread-read', args=[pk])),
        client.post(reverse(RESOLVE), {'contentType': 'core.mission', 'objectId': mission.pk}, format='json'),
        client.delete(reverse('chat-api:message-detail', args=[message.pk])),
        client.get(reverse('chat-api:unread')),
        client.get(reverse('chat-api:config')),
    ]

    assert [r.status_code for r in responses] == [403] * len(responses)
    assert responses[0].json()['detail'] == 'This feature is not enabled.'


def test_config_lists_enabled_types(api_client, owner):
    client = api_client(user=owner)

    with override_config(CHAT_RECORD_CONTENT_TYPES='core.expense, core.project ,core.mission'):
        response = client.get(reverse('chat-api:config'))

    assert response.json() == {'recordContentTypes': ['core.expense', 'core.mission']}
