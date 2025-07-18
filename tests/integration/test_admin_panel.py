import time

import pytest

import typing

from selenium.webdriver.common.by import By
from testutils.factories import TaskFactory, TimeEntryFactory, ResourceFactory, SpecialLeaveReasonFactory
from django.contrib.auth.models import Permission

if typing.TYPE_CHECKING:
    from testutils.selenium import AppTestBrowser

pytestmark = [pytest.mark.selenium, pytest.mark.django_db]


def test_admin_should_see_all_time_entries(browser: 'AppTestBrowser', admin_user_with_plain_password):
    task_1 = TaskFactory()
    task_2 = TaskFactory()
    TimeEntryFactory(task=task_1)
    TimeEntryFactory(task=task_2)

    browser.admin_user = admin_user_with_plain_password
    browser.login()
    browser.click('//a[@href="/admin/core/timeentry/" and text() = "Time entries"]')
    table_rows = browser.find_elements(By.XPATH, '//table[@id="result_list"]/tbody/tr')
    assert len(table_rows) == 2


def test_staff_user_with_perms_should_see_time_all_time_entries(browser: 'AppTestBrowser', staff_user):
    resource_1 = ResourceFactory(user=staff_user)
    staff_user.user_permissions.add(Permission.objects.get(codename='view_any_timesheet'),
                                    Permission.objects.get(codename='view_timeentry'))

    task_1 = TaskFactory()
    task_2 = TaskFactory()
    task_3 = TaskFactory(resource=resource_1)

    TimeEntryFactory(task=task_1)
    TimeEntryFactory(task=task_2)
    TimeEntryFactory(task=task_3, resource=resource_1)

    browser.admin_user = staff_user
    browser.login()

    browser.click('//a[@href="/admin/core/timeentry/" and text() = "Time entries"]')

    table_rows = browser.find_elements(By.XPATH, '//table[@id="result_list"]/tbody/tr')
    assert len(table_rows) == 3


def test_staff_user_without_perms_should_see_only_own_entries(browser: 'AppTestBrowser', staff_user):
    resource_1 = ResourceFactory(user=staff_user)

    permission = Permission.objects.get(codename='view_timeentry')
    staff_user.user_permissions.add(permission)

    task_1 = TaskFactory()
    task_2 = TaskFactory()
    task_3 = TaskFactory(resource=resource_1)

    TimeEntryFactory(task=task_1)
    TimeEntryFactory(task=task_2)
    TimeEntryFactory(task=task_3, resource=resource_1)

    browser.admin_user = staff_user
    browser.login()
    browser.click('//a[@href="/admin/core/timeentry/" and text() = "Time entries"]')

    table_rows = browser.find_elements(By.XPATH, '//table[@id="result_list"]/tbody/tr')
    assert len(table_rows) == 1


def test_admin_should_be_able_to_edit_any_time_entry(browser: 'AppTestBrowser', admin_user_with_plain_password):
    task = TaskFactory()
    time_entry = TimeEntryFactory(task=task, day_shift_hours=4)

    browser.login_as_user(admin_user_with_plain_password)
    browser.admin_user = admin_user_with_plain_password
    browser.login()
    browser.click('//a[@href="/admin/core/timeentry/" and text() = "Time entries"]')
    browser.click(f'//a[@href="/admin/core/timeentry/{time_entry.id}/change/"]')

    day_shift_input = browser.find_element(By.XPATH, '//input[@name="day_shift_hours"]')
    day_shift_input.clear()
    day_shift_input.send_keys('7')

    browser.click('//input[@value="Save"]')
    browser.click(f'//a[@href="/admin/core/timeentry/{time_entry.id}/change/"]')

    browser.assert_element('//input[@name="day_shift_hours" and @value="7.00"]')


def test_staff_user_without_manage_any_timesheet_perm_should_be_able_to_edit_only_owned_time_entry(
        browser: 'AppTestBrowser', staff_user):
    resource = ResourceFactory(user=staff_user)

    staff_user.user_permissions.add(Permission.objects.get(codename='view_any_timesheet'),
                                    Permission.objects.get(codename='view_timeentry'))

    task_1 = TaskFactory()
    owned_time_entry = TimeEntryFactory(task=task_1, day_shift_hours=4, resource=resource)

    task_2 = TaskFactory()
    not_owned_time_entry = TimeEntryFactory(task=task_2, day_shift_hours=5)

    browser.admin_user = staff_user
    browser.login()

    browser.click('//a[@href="/admin/core/timeentry/" and text() = "Time entries"]')

    browser.click(f'//a[@href="/admin/core/timeentry/{not_owned_time_entry.id}/change/"]')
    time.sleep(2)
    browser.assert_element_absent('//input[@name="day_shift_hours"]')

    browser.click('//a[@href="/admin/core/timeentry/" and text() = "Time entries"]')
    browser.click(f'//a[@href="/admin/core/timeentry/{owned_time_entry.id}/change/"]')

    day_shift_input = browser.find_element(By.XPATH, '//input[@name="day_shift_hours"]')
    day_shift_input.clear()
    day_shift_input.send_keys('3')

    browser.click('//input[@value="Save"]')
    browser.click(f'//a[@href="/admin/core/timeentry/{owned_time_entry.id}/change/"]')

    browser.assert_element('//input[@name="day_shift_hours" and @value="3.00"]')


def test_staff_user_with_manage_any_timesheet_perm_should_be_able_to_edit_any_time_entry(
        browser: 'AppTestBrowser', staff_user):

    staff_user.user_permissions.add(Permission.objects.get(codename='manage_any_timesheet'),
                                    Permission.objects.get(codename='change_timeentry'))
    task = TaskFactory()
    time_entry = TimeEntryFactory(task=task, day_shift_hours=4)

    browser.admin_user = staff_user
    browser.login()
    browser.click('//a[@href="/admin/core/timeentry/" and text() = "Time entries"]')
    browser.click(f'//a[@href="/admin/core/timeentry/{time_entry.id}/change/"]')

    day_shift_input = browser.find_element(By.XPATH, '//input[@name="day_shift_hours"]')
    day_shift_input.clear()
    day_shift_input.send_keys('2')

    browser.click('//input[@value="Save"]')
    browser.click(f'//a[@href="/admin/core/timeentry/{time_entry.id}/change/"]')

    browser.assert_element('//input[@name="day_shift_hours" and @value="2.00"]')


def test_admin_should_be_able_to_add_time_entry_for_any_resource(browser: 'AppTestBrowser',
                                                                 admin_user_with_plain_password):
    task = TaskFactory()

    ResourceFactory(user=admin_user_with_plain_password)

    browser.admin_user = admin_user_with_plain_password
    browser.login()

    browser.click('//a[@href="/admin/core/timeentry/add/"]')

    day_shift_input = browser.find_element(By.XPATH, '//input[@name="day_shift_hours"]')
    day_shift_input.clear()
    day_shift_input.send_keys('2')
    browser.click('//p/span/a[@href="#" and text()="Today"]')
    browser.click('//select[@id="id_task"]')

    browser.click(f'//option[contains(text(), "{task.title}")]')

    browser.click('//select[@id="id_resource"]')

    resource_options = browser.find_elements(By.XPATH, '//select[@id="id_resource"]/option')

    assert len(resource_options) == 3

    browser.click(f'//option[contains(text(), "{task.resource.last_name}")]')

    browser.click('//input[@value="Save"]')
    browser.assert_element('//li[@class="success"]')


def test_staff_user_with_manage_any_timesheet_perm_should_be_able_to_add_time_entry_for_any_resource(
        browser: 'AppTestBrowser', staff_user):
    staff_user.user_permissions.add(Permission.objects.get(codename='manage_any_timesheet'),
                                    Permission.objects.get(codename='view_timeentry'))
    task = TaskFactory()

    ResourceFactory(user=staff_user)

    browser.admin_user = staff_user
    browser.login()

    browser.click('//a[@href="/admin/core/timeentry/add/"]')

    day_shift_input = browser.find_element(By.XPATH, '//input[@name="day_shift_hours"]')
    day_shift_input.clear()
    day_shift_input.send_keys('2')
    browser.click('//p/span/a[@href="#" and text()="Today"]')
    browser.click('//select[@id="id_task"]')

    browser.click(f'//option[contains(text(), "{task.title}")]')

    browser.click('//select[@id="id_resource"]')

    resource_options = browser.find_elements(By.XPATH, '//select[@id="id_resource"]/option')
    assert len(resource_options) == 3

    browser.click(f'//option[contains(text(), "{task.resource.last_name}")]')

    browser.click('//input[@value="Save"]')
    browser.assert_element('//li[@class="success"]')


def test_staff_user_without_manage_any_timesheet_perm_should_be_able_to_add_time_entry_only_for_owned_resource(
        browser: 'AppTestBrowser', staff_user):
    staff_user.user_permissions.add(Permission.objects.get(codename='add_timeentry'))

    owned_resource = ResourceFactory(user=staff_user)
    task = TaskFactory(resource=owned_resource)

    browser.admin_user = staff_user
    browser.login()

    browser.click('//a[@href="/admin/core/timeentry/add/"]')

    day_shift_input = browser.find_element(By.XPATH, '//input[@name="day_shift_hours"]')
    day_shift_input.clear()
    day_shift_input.send_keys('2')
    browser.click('//p/span/a[@href="#" and text()="Today"]')
    browser.click('//select[@id="id_task"]')

    browser.click(f'//option[contains(text(), "{task.title}")]')

    browser.click('//select[@id="id_resource"]')

    resource_options = browser.find_elements(By.XPATH, '//select[@id="id_resource"]/option')
    assert len(resource_options) == 2

    browser.click(f'//option[contains(text(), "{owned_resource.last_name}")]')

    browser.click('//input[@value="Save"]')
    browser.assert_element('//li[@class="success"]')

def test_special_leave_reasons_are_displayed_in_report(browser: 'AppTestBrowser', admin_user_with_plain_password):

    resource = ResourceFactory(user=admin_user_with_plain_password)

    TimeEntryFactory(resource=resource,task=TaskFactory(resource=resource), day_shift_hours=2, date='2025-07-04')
    special_leave_reason_1 = SpecialLeaveReasonFactory()
    special_leave_reason_2 = SpecialLeaveReasonFactory()
    TimeEntryFactory(resource=resource, special_leave_hours=1, date='2025-07-04',
                     special_leave_reason=special_leave_reason_1, day_shift_hours=0)
    TimeEntryFactory(resource=resource, special_leave_hours=3, date='2025-07-06',
                     special_leave_reason=special_leave_reason_1, day_shift_hours=0)
    TimeEntryFactory(resource=resource, special_leave_hours=3, date='2025-07-05',
                     special_leave_reason=special_leave_reason_2, day_shift_hours=0)
    browser.admin_user = admin_user_with_plain_password
    browser.login()

    browser.click('//a[@href="/admin/core/timeentry/"]')
    browser.click('//a[@href="/admin/core/timeentry/report/?"]')

    reason_1_row = browser.find_elements(
        By.XPATH,
        f'//tr[./td[contains(text(), "Perm. speciale ({special_leave_reason_1.title})")]]/td'
    )

    assert reason_1_row[1].text == '4'
    assert reason_1_row[5].text == '1'
    assert reason_1_row[7].text == '3'
    reason_2_row = browser.find_elements(
        By.XPATH,
        f'//tr[./td[contains(text(), "Perm. speciale ({special_leave_reason_2.title})")]]/td'
    )
    assert reason_2_row[1].text == '3'
    assert reason_2_row[6].text == '3'
