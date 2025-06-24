import time
import typing
import datetime
import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
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

    today_str = datetime.date(2025, 6, 24).strftime("%a %b %d %Y")  # 'Tue Jun 24 2025'

    xpath = f'//div[starts-with(@id, "{today_str}")]/descendant::svg[contains(@class, "lucide-plus")]'

    el = WebDriverWait(browser, 10).until(
        EC.element_to_be_clickable((By.XPATH, xpath))
    )
    el.click()