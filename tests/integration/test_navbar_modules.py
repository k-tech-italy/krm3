import pytest


@pytest.mark.selenium
@pytest.mark.django_db
def test_navbar_report_module_regular_user(browser, regular_user, resource_factory):
    _ = resource_factory(user=regular_user)
    browser.login_as_user(regular_user)
    browser.click('[href*="be/"]')
    # Unfortunately we cannot log in using the admin login
    # as it require the flag isStaff to be true even though the
    # /be/ endpoints are accessible for all authenticated user
    # the shortcut in thi situation us the google authentication
    # in the admin login that is not testable here
    browser.assert_url_contains('/admin/login/?next=/be/')


@pytest.mark.selenium
@pytest.mark.django_db
def test_navbar_report_module_admin_user(browser, admin_user_with_plain_password, resource_factory):
    _ = resource_factory(user=admin_user_with_plain_password)
    browser.login_as_user(admin_user_with_plain_password)
    browser.click('[href*="be/"]')
    browser.assert_url_contains('/admin/login/?next=/be/')
    browser.type('input[name=username]', f'{admin_user_with_plain_password.username}')
    browser.type('input[name=password]', f'{admin_user_with_plain_password._password}')
    browser.submit('input[value="Log in"]')
    browser.wait_for_ready_state_complete()
    browser.wait_for_element_visible('//a[contains(text(), "Report")]')
    browser.wait_for_element_visible('//a[contains(text(), "Report by task")]')
    browser.wait_for_element_visible('//a[contains(text(), "Availability report")]')
