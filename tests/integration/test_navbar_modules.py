import pytest


@pytest.mark.selenium
@pytest.mark.django_db
def test_navbar_report_module_regular_user(browser, regular_user, resource_factory):
    _ = resource_factory(user=regular_user)
    browser.login_as_user(regular_user)
    browser.click('[href*="be/"]')
    # With session-based auth, the React login session now works for Django views
    # The /be/ endpoints are accessible for all authenticated users
    browser.assert_url_contains('/be/')
    browser.wait_for_element_visible('//a[contains(text(), "Report")]')
    browser.wait_for_element_visible('//a[contains(text(), "Report by task")]')
    browser.wait_for_element_visible('//a[contains(text(), "Availability report")]')


@pytest.mark.selenium
@pytest.mark.django_db
def test_navbar_report_module_admin_user(browser, admin_user_with_plain_password, resource_factory):
    _ = resource_factory(user=admin_user_with_plain_password)
    browser.login_as_user(admin_user_with_plain_password)
    browser.click('[href*="be/"]')
    # With session-based auth, no need for separate admin login
    browser.assert_url_contains('/be/')
    browser.wait_for_element_visible('//a[contains(text(), "Report")]')
    browser.wait_for_element_visible('//a[contains(text(), "Report by task")]')
    browser.wait_for_element_visible('//a[contains(text(), "Availability report")]')
