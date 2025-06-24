 
import datetime
import time

import pytest

import typing

from testutils.factories import TaskFactory
from freezegun import freeze_time

if typing.TYPE_CHECKING:
    from testutils.selenium import AppTestBrowser

pytestmark = pytest.mark.selenium
from selenium.webdriver import ActionChains

@freeze_time('2025-06-13')
@pytest.mark.selenium
@pytest.mark.django_db
def test_entries_exceed_24h(browser: 'AppTestBrowser', regular_user, resource_factory):
    resource = resource_factory(user=regular_user)

    TaskFactory(
        resource=resource,
        start_date=datetime.date(2025, 6, 1),
        end_date=datetime.date(2025, 6, 30),
    )
    TaskFactory(
        resource=resource,
        start_date=datetime.date(2025, 6, 1),
        end_date=datetime.date(2025, 6, 30),
    )

    browser.login_as_user(regular_user)
    time.sleep(2)
    browser.click('[href*="/timesheet"]')
    time.sleep(2)

    entry_tile_1 = browser.find_element('xpath','//div[contains(@id, "draggable-Mon Jun 02")]')
    actions = ActionChains(browser.driver)

    actions.click_and_hold(entry_tile_1).pause(1).release().perform()

    browser.click('//*[contains(text(), "More")]')
    browser.fill('//input[@id="daytime-input"]', '14')
    browser.click('//button/span[contains(text(), "Save")]')

    time.sleep(2)
    entry_tile_2 = browser.find_element('xpath','//div[contains(@id, "draggable-Mon Jun 02")]')
    actions.click_and_hold(entry_tile_2).pause(1).release().perform()
    browser.click('//*[contains(text(), "More")]')
    browser.fill('//input[@id="daytime-input"]', '13')
    browser.click('//button/span[contains(text(), "Save")]')

    browser.assert_element(
        '//p[@id="creation-error-message" '
        'and text()="Invalid time entry for 2025-06-02: Total hours on all time entries on 2025-06-02 (27.00) is over 24 hours."]')


    browser.click('//button[@aria-label="Close modal"]')


    browser.assert_element('//div[contains(@id, "draggable")]//span[contains(text(), "14")]')
    browser.assert_element_absent('//div[contains(@id, "draggable")]//span[contains(text(), "13")]')