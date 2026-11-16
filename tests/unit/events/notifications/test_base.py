import pytest

from krm3.events.notifications.base import Notification


def test_notification_is_abstract() -> None:
    with pytest.raises(TypeError):
        Notification()
