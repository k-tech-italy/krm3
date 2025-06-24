import time
import datetime
import typing

import pytest
from freezegun import freeze_time
from testutils.factories import TaskFactory
from selenium.webdriver.common.by import By

if typing.TYPE_CHECKING:
    from testutils.selenium import AppTestBrowser


@freeze_time('2025-06-24')
@pytest.mark.selenium
@pytest.mark.django_db
def test_timesheet_data_for_current_week(browser: 'AppTestBrowser', regular_user, resource_factory):
    resource = resource_factory(user=regular_user)

    TaskFactory(
        resource=resource,
        start_date=datetime.date(2025, 6, 1),
        end_date=datetime.date(2025, 6, 30),
    )

    browser.login_as_user(regular_user)
    browser.click('[href*="/timesheet"]')
    browser.click('//input[@id="switch-month-on"]')
    #browser.assert_element('//span[@id="date-range-display" and text()="Jun 23 - Jun 29"]')
    #span_jun23 = browser.find_elements(By.XPATH, '//span[text()="Jun 23"]')
    #span_jun29 = browser.find_elements(By.XPATH, '//span[text()="Jun 29"]')

    #assert len(span_jun23) >= 1, "Non trovato <span> con 'Jun 23'"
    #assert len(span_jun29) >= 1, "Non trovato <span> con 'Jun 29'"
    span_jun23 = browser.find_elements(By.XPATH, '//span[normalize-space(text())="Jun 23"]')
    span_jun29 = browser.find_elements(By.XPATH, '//span[normalize-space(text())="Jun 29"]')

    assert span_jun23, "❌ Nessun <span> trovato con testo esatto 'Jun 23'"
    assert span_jun29, "❌ Nessun <span> trovato con testo esatto 'Jun 29'"