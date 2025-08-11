from urllib.request import Request
from krm3.core.flags import has_group
import pytest
from django.contrib.auth.models import AnonymousUser

from testutils.factories import GroupFactory, UserFactory

def test_has_group_without_user_or_request():
    assert has_group('some-group') is False
    request = Request('http://testserver.com')
    assert has_group('some-group', request=request) is False

def test_has_group_not_authenticated_user():
    request = Request('http://testserver.com')
    request.user = AnonymousUser() # type: ignore
    assert has_group('some-group', request=request) is False

@pytest.mark.django_db
def test_has_group_user_without_groups(regular_user):
    request = Request('http://testserver.com')
    request.user = regular_user # type: ignore
    assert len(regular_user.groups.all()) == 0
    assert has_group('some-group', request=request) is False

@pytest.mark.django_db
def test_has_group_user_with_group():
    request = Request('http://testserver.com')
    role = GroupFactory(name='some-group')
    user = UserFactory()
    user.groups.add(role)
    request.user = user # type: ignore
    assert has_group('some-group', request=request) is True
