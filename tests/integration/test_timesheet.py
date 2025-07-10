import time
import datetime
import typing
import pytest

from django.test import override_settings

from testutils.factories import TaskFactory, TimeEntryFactory, ResourceFactory
from selenium.webdriver.common.by import By


from freezegun import freeze_time

if typing.TYPE_CHECKING:
    from testutils.selenium import AppTestBrowser

pytestmark = pytest.mark.selenium


@pytest.fixture(autouse=True)
def flag_timesheet():
    with override_settings(FLAGS={"TIMESHEET_ENABLED": [("boolean", True)]}):
        yield


@freeze_time('2025-06-19')
@pytest.mark.selenium
@pytest.mark.django_db
def test_timesheet_data_for_current_week(browser: 'AppTestBrowser', regular_user, resource_factory,
                                         freeze_frontend_time):
    freeze_frontend_time('2025-06-19T00:00:00Z')
    resource = resource_factory(user=regular_user)

    TaskFactory(
        resource=resource,
        start_date=datetime.date(2025, 6, 1),
        end_date=datetime.date(2025, 6, 30),
    )

    browser.login_as_user(regular_user)
    browser.click('[href*="/timesheet"]')
    browser.click('//input[@id="switch-month-on"]')

    browser.assert_element('//div[contains(., "Jun 2") and contains(., "Jun 8") and text()="-"]')

@freeze_time('2025-06-06')
@pytest.mark.selenium
@pytest.mark.django_db
def test_timesheet_no_data_only_next_month(browser: 'AppTestBrowser', regular_user, resource_factory,
                                           freeze_frontend_time):
    freeze_frontend_time('2025-06-06T00:00:00Z')
    resource = resource_factory(user=regular_user)

    # Task che inizierà nel mese successivo
    TaskFactory(
        resource=resource,
        start_date=datetime.date(2025, 7, 1),
        end_date=datetime.date(2025, 7, 30),
    )

    browser.login_as_user(regular_user)
    browser.click('[href*="/timesheet"]')
    browser.assert_element("//div[text()='No tasks available']")

@freeze_time('2025-06-06')
@pytest.mark.selenium
@pytest.mark.django_db
def test_timesheet_no_data_only_prev_month(browser: 'AppTestBrowser', regular_user, resource_factory,
                                           freeze_frontend_time):
    freeze_frontend_time('2025-06-06T00:00:00Z')
    resource = resource_factory(user=regular_user)

    # Task che è finito nel mese precedente
    TaskFactory(
        resource=resource,
        start_date=datetime.date(2025, 5, 1),
        end_date=datetime.date(2025, 5, 31),
    )

    browser.login_as_user(regular_user)
    browser.click('[href*="/timesheet"]')
    browser.assert_element("//div[text()='No tasks available']")


@freeze_time('2025-06-06')
@pytest.mark.selenium
@pytest.mark.django_db
def test_timesheet_no_data_for_current_period(browser: 'AppTestBrowser', regular_user, resource_factory,
                                              freeze_frontend_time):
    resource = resource_factory(user=regular_user)
    freeze_frontend_time('2025-06-06T00:00:00Z')
    # Task che inizierà nel mese successivo
    TaskFactory(
        resource=resource,
        start_date=datetime.date(2025, 7, 1),
        end_date=datetime.date(2025, 7, 30),
    )

    browser.login_as_user(regular_user)
    browser.click('[href*="/timesheet"]')
    browser.assert_element("//div[text()='No tasks available']")


@freeze_time('2025-06-25')
@pytest.mark.selenium
@pytest.mark.django_db
def test_timesheet_quick_add(browser: 'AppTestBrowser', regular_user, resource_factory, freeze_frontend_time):
    resource = resource_factory(user=regular_user)
    freeze_frontend_time('2025-06-25T00:00:00Z')
    TaskFactory(
        resource=resource,
        start_date=datetime.date(2025, 6, 1),
        end_date=datetime.date(2025, 6, 30),
    )

    browser.login_as_user(regular_user)
    browser.click('[href*="/timesheet"]')

    element = browser.wait_for_element_visible(
        By.XPATH, '//div[@role="button" and starts-with(@id, "Wed Jun 25 2025")]'
    )

    browser.click_and_release(element)

    browser.find_element(By.XPATH, '//button[text()="4h"]').click()

    # id for cell = Thu Jun 19 2025-9-456
    #  ADD ASSERT
    browser.assert_element(By.XPATH, '//div[starts-with(@id, "Wed Jun 25 2025")]//span[text()="4"]')


@freeze_time('2025-06-06')
@pytest.mark.selenium
@pytest.mark.django_db
def test_timesheet_no_tasks_defined(browser: 'AppTestBrowser', regular_user, resource_factory):
    resource_factory(user=regular_user)

    # Nessun task creato

    browser.login_as_user(regular_user)
    browser.click('[href*="/timesheet"]')
    browser.assert_element("//div[text()='No tasks available']")

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
    browser.click('[href*="/timesheet"]')

    entry_tile_1 = browser.wait_for_element_visible('xpath', '//div[contains(@id, "Mon Jun 02")]')
    browser.click_and_release(entry_tile_1)

    browser.click('//*[contains(text(), "More")]')

    browser.fill('//input[@id="daytime-input"]', '14')
    browser.click('//button/span[contains(text(), "Save")]')

    time.sleep(2)

    entry_tile_2 = browser.find_elements('xpath','//div[starts-with(@id, "Mon Jun 02")]')[1]
    browser.click_and_release(entry_tile_2)

    browser.click('//*[contains(text(), "More")]')
    browser.fill('//input[@id="daytime-input"]', '13')

    browser.click('//button/span[contains(text(), "Save")]')

    browser.assert_element('//p[@id="creation-error-message" and text()="Invalid time entry for 2025-06-02: '
                           'Total hours on all time entries on 2025-06-02 (27.00) is over 24 hours."]')

    browser.click('//button[@aria-label="Close modal"]')

    browser.assert_element('//div[contains(@id, "Mon Jun 02 2025")]//span[contains(text(), "14")]')
    browser.assert_element_absent('//div[contains(@id, "Mon Jun 02 2025")]//span[contains(text(), "13")]')


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
    browser.assert_element(f'//div[div[text()="{task_1.title}"] and following-sibling::div[p[text()="2"]]]')
    browser.assert_element(f'//div[div[text()="{task_2.title}"] and following-sibling::div[p[text()="5"]]]')
    browser.assert_element(f'//div[div[text()="{task_3.title}"] and following-sibling::div[p[text()="8"]]]')

    # check total hours for days
    browser.assert_element('//div[@id="column-20"]/div/div/div/div[contains(., "14h")]')
    browser.assert_element('//div[@id="column-21"]/div/div/div/div[contains(., "1h")]')

    entry_tile = browser.find_element('xpath', '//div[contains(@id, "Fri May 02")]')

    # Perform drag and drop with minimal offset
    browser.click_and_release(entry_tile)

    browser.wait_for_element('//*[contains(text(), "More")]', timeout=5)
    browser.click('//*[contains(text(), "More")]')
    browser.assert_element('//button/span[contains(text(), "Save")]')
