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


@freeze_time('2025-06-20')
@pytest.mark.selenium
@pytest.mark.django_db
def test_timesheet_quick_add(browser: 'AppTestBrowser', regular_user, resource_factory):
    resource = resource_factory(user=regular_user)

    TaskFactory(
        resource=resource,
        start_date=datetime.date(2025, 6, 1),
        end_date=datetime.date(2025, 6, 30),
    )

    browser.login_as_user(regular_user)
    time.sleep(2)
    browser.click('[href*="/timesheet"]')
    time.sleep(2)

    element = browser.driver.find_element(By.XPATH, '//div[starts-with(@id, "draggable-Thu Jun 19 2025")]')
    ActionChains(browser.driver).click_and_hold(element).move_by_offset(-1, 0).release().perform()

    browser.find_element(By.XPATH, '//button[text()="4h"]').click()
    time.sleep(4)

    # id for cell = Thu Jun 19 2025-9-456
    #  ADD ASSERT
    browser.assert_text('4h', selector='//td[contains(text(), "Thu Jun 19 2025")]/following-sibling::span')

    # Verifica che il task sia presente nella UI
    # browser.assert_text('4h', selector=f'//td[contains(text(), "{today_str}")]/following-sibling::td')


#  TEST drag and drop su 1 cella, cliccare more, si apre la modale, aggiungere ore
#  TEST drag and drop su piu' celle, cliccare 4 ed aggingere ore
#  TEST drag and drop su 1 giorno (header),si apre la modale ed aggiungere holiday
#  TEST drag and drop su piu' giorni, si apre la modale ed aggiungere holiday
