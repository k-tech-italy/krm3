import pytest

from testutils.selenium import AppTestBrowser


@pytest.mark.django_db
def test_login_ok(browser: AppTestBrowser, regular_user):
    browser.open('/')
    browser.type("#username", regular_user.username)
    browser.type("#password", "password")
    browser.click('button[type="submit"]')
    browser.assert_text(regular_user.email, selector="strong", timeout=2)

@pytest.mark.django_db
def test_login_nok(browser: AppTestBrowser, regular_user):
    browser.open('/')
    browser.type("#username", regular_user.username)
    browser.type("#password", "wrong")
    browser.click('button[type="submit"]')
    browser.assert_text("Login failed. Please try again.", selector='span', timeout=2)
