import datetime
import typing

import pytest
from freezegun import freeze_time
from testutils.factories import TaskFactory

if typing.TYPE_CHECKING:
    from testutils.selenium import AppTestBrowser


@freeze_time('2025-06-06')
@pytest.mark.selenium
@pytest.mark.django_db
def test_timesheet_no_data_only_next_month(browser: 'AppTestBrowser', regular_user, resource_factory):
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
def test_timesheet_no_data_only_prev_month(browser: 'AppTestBrowser', regular_user, resource_factory):
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
def test_timesheet_no_tasks_defined(browser: 'AppTestBrowser', regular_user, resource_factory):
    resource_factory(user=regular_user)

    # Nessun task creato

    browser.login_as_user(regular_user)
    browser.click('[href*="/timesheet"]')
    browser.assert_element("//div[text()='No tasks available']")