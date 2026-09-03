from django import test as django_test

import pytest

from testutils.factories import ResourceFactory

pytestmark = [pytest.mark.selenium, pytest.mark.django_db]


def test_navbar_report_module_regular_user(browser, regular_user):
    _ = ResourceFactory(user=regular_user)
    browser.login_as_user(regular_user)
    browser.click('[href*="be/"]')
    # With session-based auth, the React login session now works for Django views
    # The /be/ endpoints are accessible for all authenticated users
    browser.assert_url_contains('/be/')
    browser.assert_element_present('//a[contains(text(), "Report")]')
    browser.assert_element_present('//a[contains(text(), "Report by task")]')
    browser.assert_element_present('//a[contains(text(), "Availability report")]')


def test_navbar_report_module_admin_user(browser, admin_user):
    _ = ResourceFactory(user=admin_user)
    browser.login_as_user(admin_user)
    browser.click('[href*="be/"]')
    # With session-based auth, no need for separate admin login
    browser.assert_url_contains('/be/')
    browser.assert_element_present('//a[contains(text(), "Report")]')
    browser.assert_element_present('//a[contains(text(), "Report by task")]')
    browser.assert_element_present('//a[contains(text(), "Availability report")]')


@django_test.override_settings(FLAGS={'CONTACTS_ENABLED': [('boolean', True)]})
def test_navbar_contacts_module_link_visible_with_feature_flag_on(
    browser, admin_user, resource_factory
):
    _resource = ResourceFactory(user=admin_user)
    browser.login_as_user(admin_user)
    browser.assert_element_present('//a[@href="contacts" and text()="Contacts"]')


@django_test.override_settings(FLAGS={'CONTACTS_ENABLED': [('boolean', False)]})
def test_navbar_contacts_module_link_not_visible_with_feature_flag_off(
    browser, admin_user, resource_factory
):
    _resource = ResourceFactory(user=admin_user)
    browser.login_as_user(admin_user)
    browser.assert_element_absent('//a[@href="contacts" and text()="Contacts"]')
