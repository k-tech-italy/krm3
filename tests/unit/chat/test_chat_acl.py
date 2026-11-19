import pytest
from rest_framework.reverse import reverse
from testutils.factories import UserFactory

from krm3.chat import services
from krm3.chat.acl import accessible_threads, can_access_thread
from krm3.chat.registry import enabled_content_types

LABELS = [
    pytest.param(label, id=label.split('.')[1])
    for label in ('core.mission', 'core.expense', 'core.dayentry', 'core.taskentry', 'core.timesheetsubmission')
]

ROLES = [
    pytest.param('owner', True, id='owner'),
    pytest.param('viewer', True, id='view-only'),
    pytest.param('manager', True, id='manager'),
    pytest.param('superuser', True, id='superuser'),
    pytest.param('unrelated', False, id='unrelated'),
]


@pytest.fixture
def actor_for(owner, admin_user, user_with_perms, record_builders):
    def fx(role, label):
        __, view_perm, manage_perm = record_builders[label]
        return {
            'owner': lambda: owner,
            'viewer': lambda: user_with_perms(view_perm),
            'manager': lambda: user_with_perms(manage_perm),
            'superuser': lambda: admin_user,
            'unrelated': lambda: UserFactory(),
        }[role]()

    return fx


@pytest.fixture
def record_thread(owner, owner_resource, record_builders):
    def fx(label):
        build, __, __ = record_builders[label]
        record = build(owner_resource)
        thread, __ = services.resolve_record_thread(owner, record, enabled_content_types()[label])
        return record, thread

    return fx


@pytest.mark.parametrize('label', LABELS)
@pytest.mark.parametrize(('role', 'allowed'), ROLES)
def test_resolve_record(api_client, actor_for, owner_resource, record_builders, label, role, allowed):
    build, __, __ = record_builders[label]
    record = build(owner_resource)
    actor = actor_for(role, label)

    response = api_client(user=actor).post(
        reverse('chat-api:thread-resolve-record'), {'contentType': label, 'objectId': record.pk}, format='json'
    )

    assert response.status_code == (201 if allowed else 404)


@pytest.mark.parametrize('label', LABELS)
@pytest.mark.parametrize(('role', 'allowed'), ROLES)
def test_read_and_post(api_client, actor_for, record_thread, label, role, allowed):
    __, thread = record_thread(label)
    client = api_client(user=actor_for(role, label))
    url = reverse('chat-api:thread-messages', args=[thread.pk])

    read = client.get(url)
    post = client.post(url, {'body': 'hello'}, format='json')
    detail = client.get(reverse('chat-api:thread-detail', args=[thread.pk]))

    assert (read.status_code, post.status_code, detail.status_code) == ((200, 201, 200) if allowed else (404, 404, 404))


@pytest.mark.parametrize('label', LABELS)
def test_anonymous_is_rejected(api_client, record_thread, label):
    record, thread = record_thread(label)
    client = api_client()

    responses = [
        client.post(reverse('chat-api:thread-resolve-record'), {'contentType': label, 'objectId': record.pk}),
        client.get(reverse('chat-api:thread-messages', args=[thread.pk])),
        client.post(reverse('chat-api:thread-messages', args=[thread.pk]), {'body': 'hi'}),
    ]

    assert {r.status_code for r in responses} <= {401, 403}


def test_acl_helper_denies_unrelated_user(mission_thread):
    unrelated = UserFactory()

    assert not can_access_thread(unrelated, mission_thread)
    assert not accessible_threads(unrelated).exists()


def test_access_is_checked_live(api_client, mission_thread, user_with_perms):
    from django.contrib.auth.models import Permission  # noqa: PLC0415

    viewer = user_with_perms('core.view_any_mission')
    url = reverse('chat-api:thread-messages', args=[mission_thread.pk])
    assert api_client(user=viewer).get(url).status_code == 200

    viewer.user_permissions.remove(Permission.objects.get(codename='view_any_mission'))
    viewer = type(viewer).objects.get(pk=viewer.pk)  # drop the permission cache

    assert api_client(user=viewer).get(url).status_code == 404


def test_record_without_user_only_for_privileged(api_client, user_with_perms):
    from testutils.factories import MissionFactory, ResourceFactory  # noqa: PLC0415

    mission = MissionFactory(resource=ResourceFactory(user=None))
    payload = {'contentType': 'core.mission', 'objectId': mission.pk}
    url = reverse('chat-api:thread-resolve-record')

    assert api_client(user=UserFactory()).post(url, payload, format='json').status_code == 404
    assert (
        api_client(user=user_with_perms('core.view_any_mission')).post(url, payload, format='json').status_code == 201
    )
