import time
import datetime
import typing
import pytest

from testutils.factories import TaskFactory
from selenium.webdriver.common.by import By
from selenium.webdriver import ActionChains

from freezegun import freeze_time

if typing.TYPE_CHECKING:
    from testutils.selenium import AppTestBrowser

pytestmark = pytest.mark.selenium

@pytest.mark.django_db
def test_login_ok(browser: 'AppTestBrowser', regular_user):
    browser.login_as_user(regular_user)
    browser.assert_text(regular_user.email, selector='strong', timeout=2)


@pytest.mark.django_db
def test_login_nok(browser: 'AppTestBrowser', regular_user):
    regular_user._password = 'wrong'
    browser.login_as_user(regular_user)
    browser.assert_text('No active account found with the given credentials', selector='span', timeout=2)


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
    browser.assert_element('//div[contains(., "Jun 16") and contains(., "Jun 22") and text()="-"]')

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
def test_timesheet_no_data_for_current_period(browser: 'AppTestBrowser', regular_user, resource_factory):
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
    time.sleep(2)
    browser.click('[href*="/timesheet"]')
    time.sleep(2)

    element = browser.driver.find_element(By.XPATH, '//div[@role="button" and starts-with(@id, "Wed Jun 25 2025")]')
    ActionChains(browser.driver).click_and_hold(element).move_by_offset(-1, 0).release().perform()

    browser.find_element(By.XPATH, '//button[text()="4h"]').click()
    time.sleep(4)

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
