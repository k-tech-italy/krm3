import time
import datetime
import typing

import pytest
from freezegun import freeze_time
from testutils.factories import TaskFactory
from selenium.webdriver.common.by import By

if typing.TYPE_CHECKING:
    from testutils.selenium import AppTestBrowser


@freeze_time('2025-06-20')
@pytest.mark.selenium
@pytest.mark.django_db
def test_timesheet_quick_add(browser: 'AppTestBrowser', regular_user, resource_factory):
    resource = resource_factory(user=regular_user)

    def crea_task():
        TaskFactory(
        resource=resource,
        start_date=datetime.date(2025, 6, 1),
        end_date=datetime.date(2025, 6, 30),
    )

    browser.login_as_user(regular_user)
    time.sleep(2)
    browser.click('[href*="/timesheet"]')
    time.sleep(2)

    # Seleziona il giorno corrente (dipende dal markup)
    #today_str = "Jun 20
    # "
    #browser.click(f'//td[contains(text(), "{today_str}")]')  # esempio con calendario

    element = driver.find_element(By.XPATH, '//div[starts-with(@id, "draggable-Thu Jun 19 2025")]')
    element.click()
    breakpoint()

    # Inserisci il task (modifica i selettori secondo il tuo form reale)
    browser.fill('input[name="hours"]', '4')
    browser.select('select[name="task_type"]', task_type.name)
    browser.click('button[type="submit"]')  # oppure il bottone con testo 'Save' ecc.

    # Verifica che il task sia presente nella UI
    browser.assert_text('4h', selector=f'//td[contains(text(), "{today_str}")]/following-sibling::td')
