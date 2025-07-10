import typing

import pytest

if typing.TYPE_CHECKING:
    from testutils.selenium import AppTestBrowser


@pytest.mark.django_db
def test_login_ok(browser: 'AppTestBrowser', regular_user):
    browser.login_as_user(regular_user)
    browser.assert_text(regular_user.email, selector='strong', timeout=2)


@pytest.mark.django_db
def test_login_nok(browser: 'AppTestBrowser', regular_user):
    regular_user._password = 'wrong'
    browser.login_as_user(regular_user)
    browser.assert_text('No active account found with the given credentials', selector='span', timeout=2)
