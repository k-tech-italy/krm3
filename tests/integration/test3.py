import time
import datetime
import typing

import pytest
from freezegun import freeze_time
from testutils.factories import TaskFactory
from selenium.webdriver.common.by import By
from selenium.webdriver import ActionChains

if typing.TYPE_CHECKING:
    from testutils.selenium import AppTestBrowser
@freeze_time('2025-07-02')
@pytest.mark.selenium
@pytest.mark.django_db
def test_timesheet_quick_add(browser: 'AppTestBrowser', regular_user, resource_factory, freeze_frontend_time):
    resource = resource_factory(user=regular_user)
    freeze_frontend_time('2025-06-25T00:00:00Z')
    TaskFactory(
        resource=resource,
        start_date=datetime.date(2025, 7, 1),
        end_date=datetime.date(2025, 7, 30),
    )

    browser.login_as_user(regular_user)
    time.sleep(2)
    browser.click('[href*="/timesheet"]')
    time.sleep(2)

    element = browser.driver.find_element(By.XPATH, '//div[@role="button" and starts-with(@id, "Wed Jul 02 2025-")]')
    ActionChains(browser.driver).click_and_hold(element).move_by_offset(-1, 0).release().perform()

    browser.find_element(By.XPATH, '//button[text()="4h"]').click()
    time.sleep(2)

    # id for cell = Thu Jun 19 2025-9-456
    #  ADD ASSERT
    browser.assert_element(By.XPATH, '//div[starts-with(@id, "Wed Jul 02 2025")]//span[text()="4"]')
