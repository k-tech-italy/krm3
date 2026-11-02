import re
import typing

import pytest
from constance import config
from constance.test import override_config
from django.test import override_settings
from freezegun import freeze_time
from krm3.core.models import TaskEntry
from selenium.webdriver.common.by import By

from testutils.date_utils import _dt
from testutils.factories import (
    ContractFactory,
    DayEntryFactory,
    ResourceFactory,
    SpecialLeaveReasonFactory,
    TaskFactory,
    TaskEntryFactory,
    TimesheetSubmissionFactory,
)

if typing.TYPE_CHECKING:
    from testutils.selenium import AppTestBrowser
    from krm3.core.models import Task

pytestmark = pytest.mark.selenium


def rgb_to_hex(rgb_string):
    """Convert RGB color string to hexadecimal"""
    # Handle rgba format by extracting just the RGB values
    if rgb_string.startswith('rgba'):
        # Extract numbers from rgba(r, g, b, a) format
        numbers = re.findall(r'\d+', rgb_string)
        r, g, b = int(numbers[0]), int(numbers[1]), int(numbers[2])
    elif rgb_string.startswith('rgb'):
        # Extract numbers from rgb(r, g, b) format
        numbers = re.findall(r'\d+', rgb_string)
        r, g, b = int(numbers[0]), int(numbers[1]), int(numbers[2])
    else:
        # Color might already be in hex or named format
        return rgb_string

    # Convert to hex
    return f'#{r:02x}{g:02x}{b:02x}'


@pytest.fixture(autouse=True)
def flag_timesheet():
    with override_settings(FLAGS={'TIMESHEET_ENABLED': [('boolean', True)]}):
        yield


@freeze_time('2025-06-19')
@pytest.mark.selenium
@pytest.mark.django_db
def test_timesheet_data_for_current_week(
    browser: 'AppTestBrowser', regular_user, freeze_frontend_time
):
    freeze_frontend_time('2025-06-19T00:00:00Z')
    resource = ResourceFactory(user=regular_user)
    ContractFactory(resource=resource)

    TaskFactory(
        resource=resource,
        period=(_dt('2025-06-01'), _dt('2025-07-01')),
    )

    browser.login_as_user(regular_user)
    browser.click('[href*="timesheet"]')
    browser.click('//input[@id="switch-month-on"]')

    browser.assert_element('//div[contains(., "Jun 16") and contains(., "Jun 22") and text()="-"]')


@freeze_time('2025-06-06')
@pytest.mark.selenium
@pytest.mark.django_db
def test_timesheet_no_data_only_next_month(
    browser: 'AppTestBrowser', regular_user, freeze_frontend_time
):
    freeze_frontend_time('2025-06-06T00:00:00Z')
    resource = ResourceFactory(user=regular_user)

    # Task che inizierà nel mese successivo
    TaskFactory(
        resource=resource,
        period=(_dt('2025-07-01'), _dt('2025-07-31')),
        contract=True,
    )

    browser.login_as_user(regular_user)
    browser.click('[href*="timesheet"]')
    browser.assert_element("//div[text()='No tasks available']")


@freeze_time('2025-06-06')
@pytest.mark.selenium
@pytest.mark.django_db
def test_timesheet_no_data_only_prev_month(browser: 'AppTestBrowser', freeze_frontend_time):
    freeze_frontend_time('2025-06-06T00:00:00Z')

    # Task che è finito nel mese precedente
    task: Task = TaskFactory(period=(_dt('2025-05-01'), _dt('2025-06-01')), contract=True)

    browser.login_as_user(task.resource.user)
    browser.click('[href*="timesheet"]')
    browser.assert_element("//div[text()='No tasks available']")


@freeze_time('2025-06-06')
@pytest.mark.selenium
@pytest.mark.django_db
def test_timesheet_no_data_for_current_period(
    browser: 'AppTestBrowser', regular_user, freeze_frontend_time
):
    resource = ResourceFactory(user=regular_user)
    freeze_frontend_time('2025-06-06T00:00:00Z')
    # Task che inizierà nel mese successivo
    TaskFactory(
        resource=resource,
        period=(_dt('2025-07-01'), _dt('2025-07-31')),
        contract=True,
    )

    browser.login_as_user(regular_user)
    browser.click('[href*="timesheet"]')
    browser.assert_element("//div[text()='No tasks available']")


@freeze_time('2025-06-25')
@pytest.mark.selenium
@pytest.mark.django_db
def test_timesheet_quick_add(browser: 'AppTestBrowser', regular_user, freeze_frontend_time):
    resource = ResourceFactory(user=regular_user)
    freeze_frontend_time('2025-06-25T00:00:00Z')
    TaskFactory(
        resource=resource,
        period=(_dt('2025-06-01'), _dt('2025-07-01')),
        contract=True,
    )

    browser.login_as_user(regular_user)
    browser.click('[href*="timesheet"]')

    element = browser.wait_for_element_visible(
        By.XPATH, '//div[@role="button" and starts-with(@id, "Wed Jun 25 2025")]'
    )

    browser.click_and_release(element)

    browser.find_element(By.XPATH, '//button[text()="4h"]').click()

    browser.assert_element(By.XPATH, '//*[text()="4"]')


@freeze_time('2025-06-06')
@pytest.mark.selenium
@pytest.mark.django_db
def test_timesheet_no_tasks_defined(browser: 'AppTestBrowser', regular_user, resource_factory):
    resource_factory(user=regular_user)

    # Nessun task creato

    browser.login_as_user(regular_user)
    browser.click('[href*="timesheet"]')
    browser.assert_element("//div[text()='No tasks available']")

@freeze_time('2025-06-13')
@pytest.mark.selenium
@pytest.mark.django_db
def test_entries_exceed_24h(browser: 'AppTestBrowser', regular_user, freeze_frontend_time):
    freeze_frontend_time('2025-06-13T00:00:00Z')
    resource = ResourceFactory(user=regular_user)
    contract = ContractFactory(resource=resource)
    task_1 = TaskFactory(
        resource=resource,
        period=(_dt('2025-06-01'), _dt('2025-07-01')),
    )
    task_2 = TaskFactory(
        resource=resource,
        period=(_dt('2025-06-01'), _dt('2025-07-01')),
    )
    existing_task_entry = TaskEntryFactory(
        resource=resource,
        task=task_1,
        day=_dt('2025-06-02'),
        day_shift_hours=8,
        night_shift_hours=8,
        travel_hours=8

    )
    day_entry = existing_task_entry.day_entry
    day_entry.due_hours = contract.get_due_hours(day_entry.day)
    day_entry.refresh(task_entries=None, drop_existing=False)

    browser.login_as_user(regular_user)
    browser.click('[href*="timesheet"]')

    entry_tile = browser.wait_for_element_visible(
        By.XPATH,
        f'//div[@role="button" and starts-with(@id, "Mon Jun 02 2025-{task_2.pk}")]',
    )
    browser.click_and_release(entry_tile)

    browser.wait_for_element_visible('#short-menu-more-button')
    browser.js_click('#short-menu-more-button')

    task_dialog = '[role="dialog"]'
    browser.wait_for_element_visible(task_dialog)
    browser.fill('#daytime-input', '1')
    browser.click('#edit-task-entry-container button[type="submit"]')

    browser.assert_element('//*[@id="creation-error-message" and normalize-space()="Maximum 24 total hours per day."]')

    assert TaskEntry.objects.filter(day_entry=day_entry, task=task_1).count() == 1
    assert not TaskEntry.objects.filter(day_entry=day_entry, task=task_2).exists()


@freeze_time('2025-05-13')
@pytest.mark.selenium
@pytest.mark.django_db
def test_display_multiple_tasks(browser: 'AppTestBrowser', regular_user, freeze_frontend_time):
    freeze_frontend_time('2025-05-13T00:00:00Z')

    resource = ResourceFactory(user=regular_user)

    task_1 = TaskFactory(
        resource=resource,
        period=(_dt('2025-05-01'), _dt('2025-05-31')),
        contract=True,
    )
    task_2 = TaskFactory(
        resource=resource,
        period=(_dt('2025-05-01'), _dt('2025-05-31')),
        contract=True,
    )
    task_3 = TaskFactory(
        resource=resource,
        period=(_dt('2025-05-01'), _dt('2025-05-31')),
        contract=True,
    )
    task_1_entry = TaskEntryFactory(
        task=task_1,
        day=_dt('2025-05-21'),
        day_shift_hours=1,
        resource=resource,
    )
    task_1_next_day_entry = TaskEntryFactory(
        task=task_1,
        day=_dt('2025-05-22'),
        day_shift_hours=1,
        resource=resource,
    )

    TaskEntryFactory(
        task=task_2,
        day_entry=task_1_entry.day_entry,
        day_shift_hours=5,
        resource=resource,
    )

    TaskEntryFactory(
        task=task_3,
        day_entry=task_1_entry.day_entry,
        day_shift_hours=8,
        resource=resource,
    )

    task_1_entry.day_entry.refresh(task_entries=None, drop_existing=False)
    task_1_next_day_entry.day_entry.refresh(task_entries=None, drop_existing=False)

    browser.login_as_user(regular_user)

    browser.click('[href*="timesheet"]')

    # check total hours for tasks
    browser.assert_element(f'//div[div[text()="{task_1.title}"] and following-sibling::div[p[text()="2"]]]')
    browser.assert_element(f'//div[div[text()="{task_2.title}"] and following-sibling::div[p[text()="5"]]]')
    browser.assert_element(f'//div[div[text()="{task_3.title}"] and following-sibling::div[p[text()="8"]]]')

    # check total hours for days
    browser.assert_element(
        '//div[@data-tooltip-id="tooltip-hours-2025-05-21" and normalize-space()="14h"]'
    )
    browser.assert_element(
        '//div[@data-tooltip-id="tooltip-hours-2025-05-22" and normalize-space()="1h"]'
    )


@freeze_time('2025-07-13')
def test_add_leave_and_special_leave(browser: 'AppTestBrowser', regular_user, freeze_frontend_time):
    freeze_frontend_time('2025-07-13T00:00:00Z')
    resource = ResourceFactory(user=regular_user)

    task_entry = TaskEntryFactory(
        resource=resource,
        task=TaskFactory(resource=resource, contract=True),
        day_shift_hours=2,
        day=_dt('2025-07-04'),
    )
    day_entry = task_entry.day_entry
    day_entry.due_hours = day_entry.contract.get_due_hours(day_entry.day)
    day_entry.refresh(task_entries=None, drop_existing=False)
    special_leave_reason = SpecialLeaveReasonFactory()

    browser.login_as_user(regular_user)
    browser.click('[href*="timesheet"]')

    day_tile = browser.wait_for_element_visible('//div[contains(@id, "column-3")]')
    browser.click_and_release(day_tile)

    browser.fill('//label[contains(text(),"Leave Hours")]/following-sibling::input', '2')
    browser.fill('//label[contains(text(),"Special Leave Hours")]/following-sibling::input', '3')

    browser.click('//select[@name="specialReason"]')
    browser.click(f'//select[@name="specialReason"]/option[text()="{special_leave_reason.title}"]')

    browser.click('//button[contains(text(), "Save")]')
    browser.assert_element('//*[@data-testid = "leave-icon-2025-07-04"]')
    browser.assert_element('//div[@data-tooltip-id="tooltip-hours-2025-07-04" and contains(text(), "7")]')


@freeze_time('2025-07-13')
def test_sum_of_leave_special_leave_and_day_entries_cannot_exceed_8h(
    browser: 'AppTestBrowser', regular_user, freeze_frontend_time
):
    freeze_frontend_time('2025-07-13T00:00:00Z')
    resource = ResourceFactory(user=regular_user)

    task_entry = TaskEntryFactory(
        resource=resource,
        task=TaskFactory(resource=resource, contract=True),
        day_shift_hours=2,
        day=_dt('2025-07-04'),
    )
    day_entry = task_entry.day_entry
    day_entry.due_hours = day_entry.contract.get_due_hours(day_entry.day)
    day_entry.refresh(task_entries=None, drop_existing=False)
    special_leave_reason = SpecialLeaveReasonFactory()

    browser.login_as_user(regular_user)
    browser.click('[href*="timesheet"]')

    day_tile = browser.wait_for_element_visible('//div[contains(@id, "column-3")]')
    browser.click_and_release(day_tile)

    browser.fill('//label[contains(text(),"Leave Hours")]/following-sibling::input', '4')
    browser.fill('//label[contains(text(),"Special Leave Hours")]/following-sibling::input', '3')

    browser.click('//select[@name="specialReason"]')
    browser.click(f'//select[@name="specialReason"]/option[text()="{special_leave_reason.title}"]')

    browser.click('//button[contains(text(), "Save")]')

    error_element = browser.wait_for_element_visible('//p[@id="creation-error-message"]')

    expected_error = (
        'No overtime allowed when logging leave, special leave, rest or bank withdrawal hours. '
        'Maximum allowed for 2025-07-04 is 8 hours, Total hours: 9'
    )
    actual_error = error_element.text.strip()

    assert actual_error == expected_error, f'❌ Unexpected error message: {actual_error}'


@freeze_time('2025-07-13')
def test_add_bank_hours_success(browser: 'AppTestBrowser', regular_user, freeze_frontend_time):
    freeze_frontend_time('2025-07-13T00:00:00Z')
    resource = ResourceFactory(user=regular_user)

    task_entry = TaskEntryFactory(
        resource=resource,
        task=TaskFactory(resource=resource, contract=True),
        day_shift_hours=10,
        day=_dt('2025-07-04'),
    )
    day_entry = task_entry.day_entry
    day_entry.due_hours = day_entry.contract.get_due_hours(day_entry.day)
    day_entry.refresh(task_entries=None, drop_existing=False)

    browser.login_as_user(regular_user)
    browser.click('[href*="timesheet"]')

    browser.assert_element('//p[@data-testid="bank-total" and contains(text(), "0")]')
    bank_delta = browser.find_element('//p[@data-testid="bank-delta"]')
    assert bank_delta.text.strip() == '(𝚫 = +0h)'

    day_tile = browser.wait_for_element_visible('//div[contains(@data-testid, "header-2025-07-04")]')
    browser.click_and_release(day_tile)

    browser.fill('//input[contains(@id,"save-bank-hour-input")]', '2')

    browser.click('//button[contains(text(), "Save")]')

    browser.assert_element('//p[@data-testid="bank-total" and contains(text(), "2")]')
    bank_delta = browser.find_element('//p[@data-testid="bank-delta"]')
    assert bank_delta.text.strip() == '(𝚫 = +2h)'


@freeze_time('2025-07-13')
def test_use_bank_hours_success(browser: 'AppTestBrowser', regular_user, freeze_frontend_time):
    freeze_frontend_time('2025-07-13T00:00:00Z')
    resource = ResourceFactory(user=regular_user)

    banked_task_entry = TaskEntryFactory(
        resource=resource,
        task=TaskFactory(resource=resource, contract=True),
        day_shift_hours=10,
        day=_dt('2025-07-03'),
    )
    banked_day_entry = banked_task_entry.day_entry
    banked_day_entry.due_hours = banked_day_entry.contract.get_due_hours(banked_day_entry.day)
    banked_day_entry.bank = 2
    banked_day_entry.refresh(task_entries=None, drop_existing=False)

    current_task_entry = TaskEntryFactory(
        resource=resource,
        task=TaskFactory(resource=resource, contract=True),
        day_shift_hours=6,
        day=_dt('2025-07-04'),
    )
    current_day_entry = current_task_entry.day_entry
    current_day_entry.due_hours = current_day_entry.contract.get_due_hours(current_day_entry.day)
    current_day_entry.refresh(task_entries=None, drop_existing=False)

    browser.login_as_user(regular_user)
    browser.click('[href*="timesheet"]')

    browser.assert_element('//p[@data-testid="bank-total" and contains(text(), "2")]')
    bank_delta = browser.find_element('//p[@data-testid="bank-delta"]')
    assert bank_delta.text.strip() == '(𝚫 = +2h)'

    day_tile = browser.wait_for_element_visible('//div[contains(@data-testid, "header-2025-07-04")]')
    browser.click_and_release(day_tile)

    browser.fill('//input[contains(@id,"from-bank-hour-input")]', '2')

    browser.click('//button[contains(text(), "Save")]')

    browser.assert_element('//p[@data-testid="bank-total" and contains(text(), "0")]')
    bank_delta = browser.find_element('//p[@data-testid="bank-delta"]')
    assert bank_delta.text.strip() == '(𝚫 = +0h)'


@freeze_time('2025-07-13')
def test_add_bank_hours_below_scheduled_hours(browser: 'AppTestBrowser', regular_user, freeze_frontend_time):
    freeze_frontend_time('2025-07-13T00:00:00Z')
    resource = ResourceFactory(user=regular_user)

    task_entry = TaskEntryFactory(
        resource=resource,
        task=TaskFactory(resource=resource, contract=True),
        day_shift_hours=6,
        day=_dt('2025-07-04'),
    )
    day_entry = task_entry.day_entry
    day_entry.due_hours = day_entry.contract.get_due_hours(day_entry.day)
    day_entry.refresh(task_entries=None, drop_existing=False)

    browser.login_as_user(regular_user)
    browser.click('[href*="timesheet"]')

    browser.assert_element('//p[@data-testid="bank-total" and contains(text(), "0")]')
    bank_delta = browser.find_element('//p[@data-testid="bank-delta"]')
    assert bank_delta.text.strip() == '(𝚫 = +0h)'

    day_tile = browser.wait_for_element_visible('//div[contains(@data-testid, "header-2025-07-04")]')
    browser.click_and_release(day_tile)

    browser.fill('//input[contains(@id,"save-bank-hour-input")]', '2')

    browser.click('//button[contains(text(), "Save")]')

    browser.assert_element('//p[@data-testid="bank-total" and contains(text(), "0")]')
    bank_delta = browser.find_element('//p[@data-testid="bank-delta"]')
    assert bank_delta.text.strip() == '(𝚫 = +0h)'

    error_element = browser.wait_for_element_visible('//p[@id="creation-error-message"]')

    expected_error = (
        'Cannot deposit 2 bank hours for 2025-07-04. '
        'Effective hours would be 4, below the scheduled 8 hours.'
    )
    actual_error = error_element.text.strip()

    assert actual_error == expected_error, f'❌ Unexpected error message: {actual_error}'


@freeze_time('2025-07-13')
def test_save_and_use_bank_hours_in_the_same_day(browser: 'AppTestBrowser', regular_user, freeze_frontend_time):
    freeze_frontend_time('2025-07-13T00:00:00Z')
    resource = ResourceFactory(user=regular_user)

    task_entry = TaskEntryFactory(
        resource=resource,
        task=TaskFactory(resource=resource, contract=True),
        day_shift_hours=6,
        day=_dt('2025-07-04'),
    )
    day_entry = task_entry.day_entry
    day_entry.due_hours = day_entry.contract.get_due_hours(day_entry.day)
    day_entry.bank = -2
    day_entry.refresh(task_entries=None, drop_existing=False)

    browser.login_as_user(regular_user)
    browser.click('[href*="timesheet"]')

    browser.assert_element('//p[@data-testid="bank-total" and contains(text(), "2")]')
    bank_delta = browser.find_element('//p[@data-testid="bank-delta"]')
    assert bank_delta.text.strip() == '(𝚫 = -2h)'

    day_tile = browser.wait_for_element_visible('//div[contains(@data-testid, "header-2025-07-04")]')
    browser.click_and_release(day_tile)

    browser.fill('//input[contains(@id,"save-bank-hour-input")]', '2')
    browser.click('//button[contains(text(), "Save")]')

    browser.assert_element('//p[@data-testid="bank-total" and contains(text(), "0")]')
    bank_delta = browser.find_element('//p[@data-testid="bank-delta"]')
    assert bank_delta.text.strip() == '(𝚫 = +0h)'


@override_config(BANK_HOURS_LOWER_BOUND=-16.0)
@freeze_time('2025-07-13')
def test_cannot_withdraw_hours_below_lower_bound(browser: 'AppTestBrowser', regular_user, freeze_frontend_time):
    # Set the lower bound explicitly so the test does not depend on the application's default configuration.
    freeze_frontend_time('2025-07-13T00:00:00Z')
    resource = ResourceFactory(user=regular_user)
    contract = ContractFactory(resource=resource)

    DayEntryFactory(
        resource=resource,
        contract=contract,
        day=_dt('2025-07-07'),
        due_hours=contract.get_due_hours(_dt('2025-07-07')),
        bank=-8,
    )

    DayEntryFactory(
        resource=resource,
        contract=contract,
        day=_dt('2025-07-08'),
        due_hours=contract.get_due_hours(_dt('2025-07-08')),
        bank=-8,
    )

    task_entry = TaskEntryFactory(
        day_shift_hours=2,
        resource=resource,
        task=TaskFactory(resource=resource, contract=contract),
        day=_dt('2025-07-09'),
    )
    day_entry = task_entry.day_entry
    day_entry.due_hours = day_entry.contract.get_due_hours(day_entry.day)
    day_entry.refresh(task_entries=None, drop_existing=False)

    browser.login_as_user(regular_user)
    browser.click('[href*="timesheet"]')

    browser.assert_element('//p[@data-testid="bank-total" and normalize-space()="-16h"]')
    bank_delta = browser.find_element('//p[@data-testid="bank-delta"]')
    assert bank_delta.text.strip() == '(𝚫 = -16h)'

    day_tile = browser.wait_for_element_visible('//div[contains(@data-testid, "header-2025-07-09")]')
    browser.click_and_release(day_tile)

    browser.fill('//input[contains(@id,"from-bank-hour-input")]', '1')
    browser.click('//button[contains(text(), "Save")]')

    error_element = browser.wait_for_element_visible('//p[@id="creation-error-message"]')

    expected_error = (
        'This transaction would exceed the minimum bank balance of -16.0 hours. '
        'Current balance: -16.00, attempting to change by: -1.00'
    )
    actual_error = error_element.text.strip()

    assert actual_error == expected_error, f'❌ Unexpected error message: {actual_error}'


@override_config(BANK_HOURS_UPPER_BOUND=16.0)
@freeze_time('2025-07-13')
def test_cannot_exceed_bank_hours_upper_bound(browser: 'AppTestBrowser', regular_user, freeze_frontend_time):
    # Set the upper bound explicitly so the test does not depend on the application's default configuration.
    freeze_frontend_time('2025-07-13T00:00:00Z')
    resource = ResourceFactory(user=regular_user)

    first_task_entry = TaskEntryFactory(
        resource=resource,
        day_shift_hours=16,
        task=TaskFactory(resource=resource, contract=True),
        day=_dt('2025-07-07'),
    )
    first_day_entry = first_task_entry.day_entry
    first_day_entry.due_hours = first_day_entry.contract.get_due_hours(first_day_entry.day)
    first_day_entry.bank = 8
    first_day_entry.refresh(task_entries=None, drop_existing=False)

    second_task_entry = TaskEntryFactory(
        resource=resource,
        day_shift_hours=16,
        task=TaskFactory(resource=resource, contract=True),
        day=_dt('2025-07-08'),
    )
    second_day_entry = second_task_entry.day_entry
    second_day_entry.due_hours = second_day_entry.contract.get_due_hours(second_day_entry.day)
    second_day_entry.bank = 8
    second_day_entry.refresh(task_entries=None, drop_existing=False)

    current_task_entry = TaskEntryFactory(
        day_shift_hours=16,
        resource=resource,
        task=TaskFactory(resource=resource, contract=True),
        day=_dt('2025-07-09'),
    )
    current_day_entry = current_task_entry.day_entry
    current_day_entry.due_hours = current_day_entry.contract.get_due_hours(current_day_entry.day)
    current_day_entry.refresh(task_entries=None, drop_existing=False)

    browser.login_as_user(regular_user)
    browser.click('[href*="timesheet"]')

    browser.assert_element('//p[@data-testid="bank-total" and contains(text(), "16")]')
    bank_delta = browser.find_element('//p[@data-testid="bank-delta"]')
    assert bank_delta.text.strip() == '(𝚫 = +16h)'

    day_tile = browser.wait_for_element_visible('//div[contains(@data-testid, "header-2025-07-09")]')
    browser.click_and_release(day_tile)

    browser.fill('//input[contains(@id,"save-bank-hour-input")]', '8')
    browser.click('//button[contains(text(), "Save")]')

    error_element = browser.wait_for_element_visible('//p[@id="creation-error-message"]')

    expected_error = (
        'This transaction would exceed the maximum bank balance of 16.0 hours. '
        'Current balance: 16.00, attempting to add: 8.00'
    )
    actual_error = error_element.text.strip()

    assert actual_error == expected_error, f'❌ Unexpected error message: {actual_error}'


@freeze_time('2025-07-13')
def test_sick_day_wrong_protocol_number(browser: 'AppTestBrowser', regular_user, freeze_frontend_time):
    freeze_frontend_time('2025-07-13T00:00:00Z')
    resource = ResourceFactory(user=regular_user)
    TaskFactory(resource=resource, contract=True)

    browser.login_as_user(regular_user)
    browser.click('[href*="timesheet"]')

    day_header = '[data-testid="header-2025-07-04"]'
    browser.wait_for_element_visible(day_header)
    browser.js_click(day_header)
    browser.wait_for_element_visible('[role="dialog"][aria-label="Day Entry"]')

    sick_radio = '[data-testid="day-entry-sick-radio"]'
    browser.js_click(sick_radio)
    browser.wait_for_element_present(f'{sick_radio}:checked')

    protocol_number_input = '#day-entry-protocol-number-input'
    browser.wait_for_element_visible(protocol_number_input)

    # Add a wrong protocol number
    browser.fill(protocol_number_input, 'ABC3982ESA')

    browser.assert_element(
        '//*[contains(text(), "Protocol number must contain digits only.")]'
    )
    browser.assert_attribute('#day-entry-submit-button', 'disabled')


@freeze_time('2025-07-13')
def test_sick_day_empty_protocol_number(browser: 'AppTestBrowser', regular_user, freeze_frontend_time):
    freeze_frontend_time('2025-07-13T00:00:00Z')
    resource = ResourceFactory(user=regular_user)
    TaskFactory(resource=resource,  contract=True)

    browser.login_as_user(regular_user)
    browser.click('[href*="timesheet"]')

    day_header = '[data-testid="header-2025-07-04"]'
    browser.wait_for_element_visible(day_header)
    browser.js_click(day_header)
    browser.wait_for_element_visible('[role="dialog"][aria-label="Day Entry"]')

    sick_radio = '[data-testid="day-entry-sick-radio"]'
    browser.js_click(sick_radio)
    browser.wait_for_element_present(f'{sick_radio}:checked')
    browser.wait_for_element_visible('#day-entry-protocol-number-input')

    # Leaving an empty protocol number should be possible now
    browser.wait_for_element_clickable('#day-entry-submit-button')
    browser.click('#day-entry-submit-button')

    browser.wait_for_element_visible('.lucide-stethoscope')


@freeze_time('2025-07-13')
def test_sick_day_correct_protocol_number(browser: 'AppTestBrowser', regular_user, freeze_frontend_time):
    freeze_frontend_time('2025-07-13T00:00:00Z')
    resource = ResourceFactory(user=regular_user)
    TaskFactory(resource=resource, contract=True)

    browser.login_as_user(regular_user)
    browser.click('[href*="timesheet"]')

    day_header = '[data-testid="header-2025-07-04"]'
    browser.wait_for_element_visible(day_header)
    browser.js_click(day_header)
    browser.wait_for_element_visible('[role="dialog"][aria-label="Day Entry"]')

    sick_radio = '[data-testid="day-entry-sick-radio"]'
    browser.js_click(sick_radio)
    browser.wait_for_element_present(f'{sick_radio}:checked')

    protocol_number_input = '#day-entry-protocol-number-input'
    browser.wait_for_element_visible(protocol_number_input)

    # Add a protocol number with correct format (only digits)
    browser.fill(protocol_number_input, '001234985983400')

    browser.wait_for_element_clickable('#day-entry-submit-button')
    browser.click('#day-entry-submit-button')

    browser.wait_for_element_visible('.lucide-stethoscope')

    # check the protocol number is saved
    browser.js_click(day_header)
    browser.wait_for_element_visible('[role="dialog"][aria-label="Day Entry"]')
    browser.assert_attribute(protocol_number_input, 'value', '001234985983400')


@freeze_time('2025-07-13')
def test_day_entry_modal_accessible_on_timesheet_submitted(
    browser: 'AppTestBrowser', regular_user, freeze_frontend_time
):
    freeze_frontend_time('2025-07-13T00:00:00Z')
    resource = ResourceFactory(user=regular_user)
    contract = ContractFactory(resource=resource)
    TaskFactory(resource=resource, contract=contract)

    day_entry = DayEntryFactory(
        resource=resource,
        contract=contract,
        day=_dt('2025-07-04'),
        due_hours=contract.get_due_hours(_dt('2025-07-04')),
        closed=True,
    )

    submission = TimesheetSubmissionFactory(
        resource=resource,
        closed=True,
        period=(_dt('2025-07-01'), _dt('2025-07-31')),
    )
    type(day_entry).objects.filter(pk=day_entry.pk).update(timesheet=submission)

    browser.login_as_user(regular_user)
    browser.click('[href*="timesheet"]')
    day_header = '[data-testid="header-2025-07-04"]'
    browser.wait_for_element_visible(day_header)
    browser.js_click(day_header)
    browser.wait_for_element_visible('[role="dialog"][aria-label="Day Entry"]')

    browser.assert_attribute('#day-entry-from-date-picker', 'disabled')
    browser.assert_attribute('#save-bank-hour-input', 'disabled')
    browser.assert_attribute('#from-bank-hour-input', 'disabled')


@freeze_time('2025-06-25')
@pytest.mark.selenium
@pytest.mark.django_db
def test_timesheet_scheduled_hours_exact_colors(
    browser: 'AppTestBrowser', regular_user, freeze_frontend_time
):
    resource = ResourceFactory(user=regular_user)
    freeze_frontend_time('2025-06-25T00:00:00Z')
    TaskFactory(
        resource=resource,
        period=(_dt('2025-06-01'), _dt('2025-07-01')),
        contract=True,
    )

    browser.login_as_user(regular_user)
    browser.click('[href*="timesheet"]')

    header_element = browser.wait_for_element_visible(By.XPATH, '//div[@data-testid="header-2025-06-24"]')
    header_color = header_element.value_of_css_property('background-color')
    assert rgb_to_hex(header_color) == config.LESS_THAN_SCHEDULE_COLOR_DARK_THEME

    element = browser.wait_for_element_visible(
        By.XPATH, '//div[@role="button" and starts-with(@id, "Tue Jun 24 2025")]'
    )

    browser.click_and_release(element)

    btn = browser.wait_for_element_visible('//button[text()="8h"]')
    btn.click()
    element_path = (
        '//div[contains(@data-testid, "header-2025-06-24") and contains(@style,'
        f' "{config.EXACT_SCHEDULE_COLOR_DARK_THEME}")]'
    )
    try:
        browser.wait_for_element_visible(element_path)
    except Exception:  # noqa: BLE001 may have failed as clicking is too quickly retrying once
        btn.click()
        browser.wait_for_element_visible(element_path)


@freeze_time('2025-06-25')
@pytest.mark.selenium
@pytest.mark.django_db
def test_timesheet_scheduled_hours_less_colors(
    browser: 'AppTestBrowser', regular_user, freeze_frontend_time
):
    resource = ResourceFactory(user=regular_user)
    freeze_frontend_time('2025-06-25T00:00:00Z')
    TaskFactory(
        resource=resource,
        period=(_dt('2025-06-01'), _dt('2025-07-01')),
        contract=True,
    )

    browser.login_as_user(regular_user)
    browser.click('[href*="timesheet"]')

    header_element = browser.wait_for_element_visible(By.XPATH, '//div[@data-testid="header-2025-06-24"]')
    header_color = header_element.value_of_css_property('background-color')
    assert rgb_to_hex(header_color) == config.LESS_THAN_SCHEDULE_COLOR_DARK_THEME

    element = browser.wait_for_element_visible(
        By.XPATH, '//div[@role="button" and starts-with(@id, "Tue Jun 24 2025")]'
    )

    browser.click_and_release(element)

    browser.find_element(By.XPATH, '//button[text()="4h"]').click()
    element_path = (
        '//div[contains(@data-testid, "header-2025-06-24") and contains(@style,'
        f' "{config.LESS_THAN_SCHEDULE_COLOR_DARK_THEME}")]'
    )
    browser.wait_for_element_visible(element_path)


@freeze_time('2025-06-25')
@pytest.mark.selenium
@pytest.mark.django_db
def test_timesheet_scheduled_hours_more_colors(
    browser: 'AppTestBrowser', regular_user, freeze_frontend_time
):
    resource = ResourceFactory(user=regular_user)
    ContractFactory(resource=resource)
    freeze_frontend_time('2025-06-25T00:00:00Z')
    TaskFactory(
        resource=resource,
        period=(_dt('2025-06-01'), _dt('2025-07-01')),
    )

    browser.login_as_user(regular_user)
    browser.click('[href*="timesheet"]')

    header_element = browser.wait_for_element_visible(By.XPATH, '//div[@data-testid="header-2025-06-24"]')
    header_color = header_element.value_of_css_property('background-color')
    assert rgb_to_hex(header_color) == config.LESS_THAN_SCHEDULE_COLOR_DARK_THEME

    element = browser.wait_for_element_visible(
        By.XPATH, '//div[@role="button" and starts-with(@id, "Tue Jun 24 2025")]'
    )

    browser.click_and_release(element)

    more_button = '#short-menu-more-button'
    browser.wait_for_element_visible(more_button)
    browser.js_click(more_button)
    task_dialog = '//div[@role="dialog" and starts-with(@aria-label, "Add Task Entry for ")]'
    browser.wait_for_element_visible(task_dialog)
    browser.fill(f'{task_dialog}//input[@id="daytime-input"]', '13')
    browser.click(f'{task_dialog}//button[normalize-space()="Save"]')
    element_path = (
        '//div[contains(@data-testid, "header-2025-06-24") and contains(@style,'
        f' "{config.MORE_THAN_SCHEDULE_COLOR_DARK_THEME}")]'
    )
    browser.wait_for_element_visible(element_path)


@freeze_time('2025-06-28')
@pytest.mark.selenium
@pytest.mark.django_db
def test_timesheet_non_working_day_more_colors(
    browser: 'AppTestBrowser', regular_user, freeze_frontend_time
):
    """Test adding hours in non-working-day is changing color to MORE_THAN_SCHEDULE_COLOR_DARK_THEME."""
    resource = ResourceFactory(user=regular_user)
    freeze_frontend_time('2025-06-28T00:00:00Z')
    TaskFactory(
        resource=resource,
        period=(_dt('2025-06-01'), _dt('2025-07-01')),
        contract=True,
    )

    browser.login_as_user(regular_user)
    browser.click('[href*="timesheet"]')

    element = browser.wait_for_element_visible(
        By.XPATH, '//div[@role="button" and starts-with(@id, "Sun Jun 29 2025")]'
    )

    browser.click_and_release(element)

    more_button = '#short-menu-more-button'
    browser.wait_for_element_visible(more_button)
    browser.js_click(more_button)
    task_dialog = '//div[@role="dialog" and starts-with(@aria-label, "Add Task Entry for ")]'
    browser.wait_for_element_visible(task_dialog)
    browser.fill(f'{task_dialog}//input[@id="daytime-input"]', '2')
    browser.click(f'{task_dialog}//button[normalize-space()="Save"]')
    element_path = (
        '//div[contains(@data-testid, "header-2025-06-29") and contains(@style,'
        f' "{config.MORE_THAN_SCHEDULE_COLOR_DARK_THEME}")]'
    )
    browser.wait_for_element_visible(element_path)
