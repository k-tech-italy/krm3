import datetime
import time

import pytest

import typing

from selenium.webdriver import ActionChains
from testutils.factories import TaskFactory, TimeEntryFactory, ResourceFactory
from freezegun import freeze_time

if typing.TYPE_CHECKING:
    from testutils.selenium import AppTestBrowser

pytestmark = pytest.mark.selenium


@freeze_time('2025-06-13')
@pytest.mark.selenium
@pytest.mark.django_db
def test_entries_exceed_24h(browser: 'AppTestBrowser', regular_user, resource_factory, freeze_frontend_time):
    resource = resource_factory(user=regular_user)

    freeze_frontend_time('2025-06-13T00:00:00Z')

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
        'and text()="Invalid time entry for 2025-06-02: '
        'Total hours on all time entries on 2025-06-02 (27.00) is over 24 hours."]')


    browser.click('//button[@aria-label="Close modal"]')

    browser.assert_element('//div[contains(@id, "draggable")]//span[contains(text(), "14")]')
    browser.assert_element_absent('//div[contains(@id, "draggable")]//span[contains(text(), "13")]')


@freeze_time('2025-05-13')
@pytest.mark.selenium
@pytest.mark.django_db
def test_display_multiple_tasks(browser: 'AppTestBrowser', regular_user, freeze_frontend_time):

    freeze_frontend_time('2025-05-13T00:00:00Z')

    resource = ResourceFactory(user=regular_user)

    task_1 = TaskFactory(
        resource=resource,
        start_date=datetime.date(2025, 5, 1),
        end_date=datetime.date(2025, 5, 30),
    )
    task_2 = TaskFactory(
        resource=resource,
        start_date=datetime.date(2025, 5, 1),
        end_date=datetime.date(2025, 5, 30),
    )
    task_3 = TaskFactory(
        resource=resource,
        start_date=datetime.date(2025, 5, 1),
        end_date=datetime.date(2025, 5, 30),
    )
    TimeEntryFactory(task=task_1,date=datetime.date(2025, 5, 21), day_shift_hours=1, resource=resource)
    TimeEntryFactory(task=task_1, date=datetime.date(2025, 5, 22), day_shift_hours=1, resource=resource)

    TimeEntryFactory(task=task_2, date=datetime.date(2025, 5, 21), day_shift_hours=5, resource=resource)

    TimeEntryFactory(task=task_3, date=datetime.date(2025, 5, 21), day_shift_hours=8, resource=resource)

    browser.login_as_user(regular_user)

    browser.click('[href*="/timesheet"]')

    # check total hours for tasks
    browser.assert_element(f'//div[div[div[text()="{task_1.title}"]] and following-sibling::div[text()="2"]]')
    browser.assert_element(f'//div[div[div[text()="{task_2.title}"]] and following-sibling::div[text()="5"]]')
    browser.assert_element(f'//div[div[div[text()="{task_3.title}"]] and following-sibling::div[text()="8"]]')

    # check total hours for days
    browser.assert_element('//div[@id="draggable-column-20"]/div/div/div/div[contains(., "14h")]')
    browser.assert_element('//div[@id="draggable-column-21"]/div/div/div/div[contains(., "1h")]')

    # check if edit menu is being opened
    entry_tile = browser.find_element('xpath', '//div[contains(@id, "draggable-Fri May 02")]')
    actions = ActionChains(browser.driver)
    actions.click_and_hold(entry_tile).pause(1).release().perform()
    browser.click('//*[contains(text(), "More")]')
    browser.assert_element('//button/span[contains(text(), "Save")]')

