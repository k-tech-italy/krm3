from django.urls import reverse
from testutils.factories import ChatMessageFactory, ChatThreadFactory, DirectChatThreadFactory

from krm3.chat import services


def test_message_admin_hides_direct_messages(admin_client):
    record_message = ChatMessageFactory(thread=ChatThreadFactory(), body='record note')
    dm = DirectChatThreadFactory()
    dm_message = ChatMessageFactory(thread=dm, author=dm.direct_user_low, body='private words')

    changelist = admin_client.get(reverse('admin:core_chatmessage_changelist'))
    change = admin_client.get(reverse('admin:core_chatmessage_change', args=[dm_message.pk]))

    assert changelist.status_code == 200
    assert 'record note' in changelist.text
    assert 'private words' not in changelist.text
    assert change.status_code == 302  # unknown object: redirected to the admin index
    assert admin_client.get(reverse('admin:core_chatmessage_change', args=[record_message.pk])).status_code == 200


def test_thread_admin_shows_dm_metadata_only(admin_client):
    dm = DirectChatThreadFactory()
    services.post_message(dm.direct_user_low, dm, 'private words')

    pages = [
        admin_client.get(reverse('admin:core_chatthread_changelist')),
        admin_client.get(reverse('admin:core_chatthread_change', args=[dm.pk])),
        admin_client.get(reverse('admin:core_chatthread_delete', args=[dm.pk])),
    ]

    for page in pages:
        assert page.status_code == 200
        assert 'private words' not in page.text
    assert str(dm.direct_user_low) in pages[0].text
