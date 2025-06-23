import datetime
import time

import pytest

import typing

from selenium.webdriver.common.by import By
from testutils.factories import TaskFactory, TimeEntryFactory, ResourceFactory, UserFactory
from django.contrib.auth.models import Permission

if typing.TYPE_CHECKING:
    from testutils.selenium import AppTestBrowser

pytestmark = pytest.mark.selenium

@pytest.mark.selenium
@pytest.mark.django_db
def test_admin_should_see_all_time_entries(browser: 'AppTestBrowser', admin_user):
    task_1 = TaskFactory()
    task_2 = TaskFactory()
    TimeEntryFactory(task=task_1)
    TimeEntryFactory(task=task_2)

    browser.login_as_user(admin_user)
    browser.admin_user = admin_user
    browser.login()
    browser.click('//a[@href="/admin/core/timeentry/" and text() = "Time entries"]')
    table_rows = browser.find_elements(By.XPATH, '//table[@id="result_list"]/tbody/tr')
    assert len(table_rows) == 2


@pytest.mark.selenium
@pytest.mark.django_db
def test_staff_user_with_perms_should_see_time_all_time_entries(browser: 'AppTestBrowser', staff_user):
    resource_1 = ResourceFactory(user=staff_user)
    permission = Permission.objects.get(codename='view_any_timesheet')
    staff_user.user_permissions.add(permission)

    task_1 = TaskFactory()
    task_2 = TaskFactory()
    task_3 = TaskFactory(resource=resource_1)

    TimeEntryFactory(task=task_1)
    TimeEntryFactory(task=task_2)
    TimeEntryFactory(task=task_3, resource=resource_1)

    browser.login_as_user(staff_user)
    browser.admin_user = staff_user
    browser.login()

    browser.click('//a[@href="/admin/core/timeentry/" and text() = "Time entries"]')

    table_rows = browser.find_elements(By.XPATH, '//table[@id="result_list"]/tbody/tr')
    assert len(table_rows) == 3

@pytest.mark.selenium
@pytest.mark.django_db
def test_staff_user_without_perms_should_see_only_own_entries(browser: 'AppTestBrowser', staff_user):
    resource_1 = ResourceFactory(user=staff_user)

    permission = Permission.objects.get(codename='view_timesheet')
    staff_user.user_permissions.add(permission)

    task_1 = TaskFactory()
    task_2 = TaskFactory()
    task_3 = TaskFactory(resource=resource_1)

    TimeEntryFactory(task=task_1)
    TimeEntryFactory(task=task_2)
    TimeEntryFactory(task=task_3, resource=resource_1)

    browser.login_as_user(staff_user)
    browser.admin_user = staff_user
    browser.login()
    browser.click('//a[@href="/admin/core/timeentry/" and text() = "Time entries"]')

    table_rows = browser.find_elements(By.XPATH, '//table[@id="result_list"]/tbody/tr')
    assert len(table_rows) == 1

