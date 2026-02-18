import datetime
import re
import typing

import pytest
from constance import config
from django.test import override_settings
from freezegun import freeze_time
from selenium.webdriver.common.by import By
from testutils.factories import (
    ContractFactory,
    ResourceFactory,
    SpecialLeaveReasonFactory,
    TaskFactory,
    TimeEntryFactory,
    TimesheetSubmissionFactory,
)

if typing.TYPE_CHECKING:
    from testutils.selenium import AppTestBrowser

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
    browser: 'AppTestBrowser', regular_user, resource_factory, freeze_frontend_time
):
    freeze_frontend_time('2025-06-19T00:00:00Z')
    resource = resource_factory(user=regular_user)
    ContractFactory(resource=resource)

    TaskFactory(
        resource=resource,
        start_date=datetime.date(2025, 6, 1),
        end_date=datetime.date(2025, 6, 30),
    )

    browser.login_as_user(regular_user)
    browser.click('[href*="timesheet"]')
    browser.click('//input[@id="switch-month-on"]')

    browser.assert_element('//div[contains(., "Jun 16") and contains(., "Jun 22") and text()="-"]')


@freeze_time('2025-06-06')
@pytest.mark.selenium
@pytest.mark.django_db
def test_timesheet_no_data_only_next_month(
    browser: 'AppTestBrowser', regular_user, resource_factory, freeze_frontend_time
):
    freeze_frontend_time('2025-06-06T00:00:00Z')
    resource = resource_factory(user=regular_user)

    # Task che inizierà nel mese successivo
    TaskFactory(
        resource=resource,
        start_date=datetime.date(2025, 7, 1),
        end_date=datetime.date(2025, 7, 30),
    )

    browser.login_as_user(regular_user)
    browser.click('[href*="timesheet"]')
    browser.assert_element("//div[text()='No tasks available']")


@freeze_time('2025-06-06')
@pytest.mark.selenium
@pytest.mark.django_db
def test_timesheet_no_data_only_prev_month(
    browser: 'AppTestBrowser', regular_user, resource_factory, freeze_frontend_time
):
    freeze_frontend_time('2025-06-06T00:00:00Z')
    resource = resource_factory(user=regular_user)

    # Task che è finito nel mese precedente
    TaskFactory(
        resource=resource,
        start_date=datetime.date(2025, 5, 1),
        end_date=datetime.date(2025, 5, 31),
    )

    browser.login_as_user(regular_user)
    browser.click('[href*="timesheet"]')
    browser.assert_element("//div[text()='No tasks available']")


@freeze_time('2025-06-06')
@pytest.mark.selenium
@pytest.mark.django_db
def test_timesheet_no_data_for_current_period(
    browser: 'AppTestBrowser', regular_user, resource_factory, freeze_frontend_time
):
    resource = resource_factory(user=regular_user)
    freeze_frontend_time('2025-06-06T00:00:00Z')
    # Task che inizierà nel mese successivo
    TaskFactory(
        resource=resource,
        start_date=datetime.date(2025, 7, 1),
        end_date=datetime.date(2025, 7, 30),
    )

    browser.login_as_user(regular_user)
    browser.click('[href*="timesheet"]')
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
def test_entries_exceed_24h(browser: 'AppTestBrowser', regular_user, resource_factory, freeze_frontend_time):
    resource = resource_factory(user=regular_user)

    freeze_frontend_time('2025-06-13T00:00:00Z')

    TaskFactory(
        resource=resource,
        start_date=datetime.date(2025, 6, 1),
        end_date=datetime.date(2025, 6, 30),
    )
    TaskFactory(
        resource=resource,
        start_date=datetime.date(2025, 6, 1),
        end_date=datetime.date(2025, 6, 30),
    )

    browser.login_as_user(regular_user)
    browser.click('[href*="timesheet"]')

    entry_tile_1 = browser.wait_for_element_visible('xpath', '//div[contains(@id, "Mon Jun 02")]')
    browser.click_and_release(entry_tile_1)

    browser.click('//*[contains(text(), "More")]')

    browser.fill('//input[@id="daytime-input"]', '14')
    browser.click('//*[contains(text(), "Save")]')

    entry_tile_2 = browser.find_elements('xpath', '//div[starts-with(@id, "Mon Jun 02")]')[1]
    browser.click_and_release(entry_tile_2)

    browser.click('//*[contains(text(), "More")]')
    browser.fill('//input[@id="daytime-input"]', '13')

    browser.click('//*[contains(text(), "Save")]')

    browser.assert_element(
        '//p[@id="creation-error-message" and text()="Invalid time entry for 2025-06-02: '
        'Total hours on all time entries on 2025-06-02 (27.00) is over 24 hours."]'
    )

    browser.click('//button[@aria-label="Close modal"]')

    browser.assert_element('//div[contains(@id, "Mon Jun 02 2025")]//span[contains(text(), "14")]')
    browser.assert_element_absent('//div[contains(@id, "Mon Jun 02 2025")]//span[contains(text(), "13")]')


@freeze_time('2025-05-13')
@pytest.mark.selenium
@pytest.mark.django_db
def test_display_multiple_tasks(browser: 'AppTestBrowser', regular_user, freeze_frontend_time):
    freeze_frontend_time('2025-05-13T00:00:00Z')

    resource = ResourceFactory(user=regular_user)

    task_1 = TaskFactory(
        resource=resource,
        start_date=datetime.date(2025, 5, 1),
        end_date=datetime.date(2025, 5, 30),
    )
    task_2 = TaskFactory(
        resource=resource,
        start_date=datetime.date(2025, 5, 1),
        end_date=datetime.date(2025, 5, 30),
    )
    task_3 = TaskFactory(
        resource=resource,
        start_date=datetime.date(2025, 5, 1),
        end_date=datetime.date(2025, 5, 30),
    )
    TimeEntryFactory(task=task_1, date=datetime.date(2025, 5, 21), day_shift_hours=1, resource=resource)
    TimeEntryFactory(task=task_1, date=datetime.date(2025, 5, 22), day_shift_hours=1, resource=resource)

    TimeEntryFactory(task=task_2, date=datetime.date(2025, 5, 21), day_shift_hours=5, resource=resource)

    TimeEntryFactory(task=task_3, date=datetime.date(2025, 5, 21), day_shift_hours=8, resource=resource)

    browser.login_as_user(regular_user)

    browser.click('[href*="timesheet"]')

    # check total hours for tasks
    browser.assert_element(f'//div[div[text()="{task_1.title}"] and following-sibling::div[p[text()="2"]]]')
    browser.assert_element(f'//div[div[text()="{task_2.title}"] and following-sibling::div[p[text()="5"]]]')
    browser.assert_element(f'//div[div[text()="{task_3.title}"] and following-sibling::div[p[text()="8"]]]')

    # check total hours for days
    browser.assert_element('//div[@id="column-20"]/div/div/div/div[contains(., "14h")]')
    browser.assert_element('//div[@id="column-21"]/div/div/div/div[contains(., "1h")]')

    entry_tile = browser.find_element('xpath', '//div[contains(@id, "Fri May 02")]')

    # Perform drag and drop with minimal offset
    browser.click_and_release(entry_tile)

    browser.wait_for_element('//*[contains(text(), "More")]', timeout=5)
    browser.click('//*[contains(text(), "More")]')
    browser.assert_element('//*[contains(text(), "Save")]')


@freeze_time('2025-07-13')
def test_add_leave_and_special_leave(browser: 'AppTestBrowser', regular_user, freeze_frontend_time):
    freeze_frontend_time('2025-07-13T00:00:00Z')
    resource = ResourceFactory(user=regular_user)

    TimeEntryFactory(resource=resource, task=TaskFactory(resource=resource), day_shift_hours=2, date='2025-07-04')
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

    TimeEntryFactory(resource=resource, task=TaskFactory(resource=resource), day_shift_hours=2, date='2025-07-04')
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
        'No overtime allowed when logging leave, special leave or rest hours. '
        'Maximum allowed for 2025-07-04 is 8 hours, Total hours: 9'
    )
    actual_error = error_element.text.strip()

    assert actual_error == expected_error, f'❌ Unexpected error message: {actual_error}'


@freeze_time('2025-07-13')
def test_add_bank_hours_success(browser: 'AppTestBrowser', regular_user, freeze_frontend_time):
    freeze_frontend_time('2025-07-13T00:00:00Z')
    resource = ResourceFactory(user=regular_user)

    TimeEntryFactory(
        resource=resource,
        task=TaskFactory(resource=resource),
        day_shift_hours=10,
        date='2025-07-04',
    )

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

    TimeEntryFactory(
        resource=resource,
        task=TaskFactory(resource=resource),
        day_shift_hours=10,
        date='2025-07-03',
    )
    TimeEntryFactory(resource=resource, task=None, bank_to=2, date='2025-07-03', day_shift_hours=0)
    TimeEntryFactory(
        resource=resource,
        task=TaskFactory(resource=resource),
        day_shift_hours=6,
        date='2025-07-04',
    )

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

    TimeEntryFactory(
        resource=resource,
        task=TaskFactory(resource=resource),
        day_shift_hours=6,
        date='2025-07-04',
    )

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
        'Invalid time entry for 2025-07-04: Cannot deposit 2.00 bank hours. '
        'Total hours would become 4.00 which is below scheduled hours (8).'
    )
    actual_error = error_element.text.strip()

    assert actual_error == expected_error, f'❌ Unexpected error message: {actual_error}'


@freeze_time('2025-07-13')
def test_save_and_use_bank_hours_in_the_same_day(browser: 'AppTestBrowser', regular_user, freeze_frontend_time):
    freeze_frontend_time('2025-07-13T00:00:00Z')
    resource = ResourceFactory(user=regular_user)

    TimeEntryFactory(
        resource=resource,
        task=TaskFactory(resource=resource),
        day_shift_hours=6,
        date='2025-07-04',
    )

    TimeEntryFactory(
        resource=resource,
        day_shift_hours=0,
        task=None,
        bank_from=2,
        date='2025-07-04',
    )

    browser.login_as_user(regular_user)
    browser.click('[href*="timesheet"]')

    browser.assert_element('//p[@data-testid="bank-total" and contains(text(), "2")]')
    bank_delta = browser.find_element('//p[@data-testid="bank-delta"]')
    assert bank_delta.text.strip() == '(𝚫 = -2h)'

    day_tile = browser.wait_for_element_visible('//div[contains(@data-testid, "header-2025-07-04")]')
    browser.click_and_release(day_tile)

    browser.fill('//input[contains(@id,"save-bank-hour-input")]', '2')
    browser.click('//button[contains(text(), "Save")]')

    error_element = browser.wait_for_element_visible('//p[@id="creation-error-message"]')

    expected_error = (
        'Invalid time entry for 2025-07-04: Cannot both withdraw from and deposit '
        'to bank hours on the same day; Cannot deposit 2.00 bank hours. Total hours '
        'would become 6.00 which is below scheduled hours (8).'
    )
    actual_error = error_element.text.strip()

    assert actual_error == expected_error, f'❌ Unexpected error message: {actual_error}'


@freeze_time('2025-07-13')
def test_cannot_withdraw_hours_below_lower_bound(browser: 'AppTestBrowser', regular_user, freeze_frontend_time):
    # NOTE: default lower bound is -16
    # FIXME: this test should also change the lower bound
    freeze_frontend_time('2025-07-13T00:00:00Z')
    resource = ResourceFactory(user=regular_user)

    TimeEntryFactory(
        resource=resource,
        day_shift_hours=0,
        task=None,
        bank_from=8,
        date='2025-07-07',
    )

    TimeEntryFactory(
        resource=resource,
        day_shift_hours=0,
        task=None,
        bank_from=8,
        date='2025-07-08',
    )

    TimeEntryFactory(
        day_shift_hours=2,
        resource=resource,
        task=TaskFactory(resource=resource),
        date='2025-07-09',
    )

    browser.login_as_user(regular_user)
    browser.click('[href*="timesheet"]')

    browser.assert_element('//p[@data-testid="bank-total" and contains(text(), "16")]')
    bank_delta = browser.find_element('//p[@data-testid="bank-delta"]')
    assert bank_delta.text.strip() == '(𝚫 = -16h)'

    day_tile = browser.wait_for_element_visible('//div[contains(@data-testid, "header-2025-07-09")]')
    browser.click_and_release(day_tile)

    browser.fill('//input[contains(@id,"from-bank-hour-input")]', '1')
    browser.click('//button[contains(text(), "Save")]')

    error_element = browser.wait_for_element_visible('//p[@id="creation-error-message"]')

    expected_error = (
        'Invalid time entry for 2025-07-09: This transaction would exceed the minimum bank'
        ' balance of -16.0 hours. Current balance: -16.00, attempting to change by: 1.00.'
    )
    actual_error = error_element.text.strip()

    assert actual_error == expected_error, f'❌ Unexpected error message: {actual_error}'


@freeze_time('2025-07-13')
def test_store_more_bank_hours_than_16(browser: 'AppTestBrowser', regular_user, freeze_frontend_time):
    # NOTE: default upper bound is 16
    # FIXME: this test should also change the upper bound
    freeze_frontend_time('2025-07-13T00:00:00Z')
    resource = ResourceFactory(user=regular_user)

    TimeEntryFactory(
        resource=resource,
        day_shift_hours=16,
        task=TaskFactory(resource=resource),
        date='2025-07-07',
    )

    TimeEntryFactory(
        resource=resource,
        day_shift_hours=0,
        task=None,
        bank_to=8,
        date='2025-07-07',
    )

    TimeEntryFactory(
        resource=resource,
        day_shift_hours=16,
        task=TaskFactory(resource=resource),
        date='2025-07-08',
    )

    TimeEntryFactory(
        resource=resource,
        day_shift_hours=0,
        task=None,
        bank_to=8,
        date='2025-07-08',
    )

    TimeEntryFactory(
        day_shift_hours=1,
        resource=resource,
        task=TaskFactory(resource=resource),
        date='2025-07-09',
    )

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
        'Invalid time entry for 2025-07-09: This transaction would exceed the maximum bank balance of 16.0 hours. '
        'Current balance: 16.00, attempting to add: -8.00; Cannot deposit 8.00 bank hours.'
        ' Total hours would become -7.00 which is below scheduled hours (8).'
    )
    actual_error = error_element.text.strip()

    assert actual_error == expected_error, f'❌ Unexpected error message: {actual_error}'


@freeze_time('2025-07-13')
def test_sick_day_wrong_protocol_number(browser: 'AppTestBrowser', regular_user, freeze_frontend_time):
    freeze_frontend_time('2025-07-13T00:00:00Z')
    resource = ResourceFactory(user=regular_user)
    TaskFactory(resource=resource)

    browser.login_as_user(regular_user)
    browser.click('[href*="timesheet"]')

    day_tile = browser.wait_for_element_visible('//div[contains(@id, "column-3")]')
    browser.click_and_release(day_tile)
    browser.click('//div[contains(@id, "day-entry-sick-days-div")]')

    # Add a wrong protocol number
    browser.fill('//textarea[contains(@id,"day-entry-protocol-number-input")]', 'ABC3982ESA')

    browser.click('//button[contains(text(), "Save")]')

    browser.assert_element(
        '//*[contains(text(), "Invalid time entry for 2025-07-04: Protocol number digits must be numeric.")]'
    )


@freeze_time('2025-07-13')
def test_sick_day_empty_protocol_number(browser: 'AppTestBrowser', regular_user, freeze_frontend_time):
    freeze_frontend_time('2025-07-13T00:00:00Z')
    resource = ResourceFactory(user=regular_user)
    TaskFactory(resource=resource)

    browser.login_as_user(regular_user)
    browser.click('[href*="timesheet"]')

    day_tile = browser.wait_for_element_visible('//div[contains(@id, "column-3")]')
    browser.click_and_release(day_tile)
    browser.click('//div[contains(@id, "day-entry-sick-days-div")]')

    # Leaving an empty protocol number should be possible now
    browser.click('//button[contains(text(), "Save")]')

    browser.assert_element('//*[contains(@class, "lucide-stethoscope")]')


@freeze_time('2025-07-13')
def test_sick_day_correct_protocol_number(browser: 'AppTestBrowser', regular_user, freeze_frontend_time):
    freeze_frontend_time('2025-07-13T00:00:00Z')
    resource = ResourceFactory(user=regular_user)
    TaskFactory(resource=resource)

    browser.login_as_user(regular_user)
    browser.click('[href*="timesheet"]')

    day_tile = browser.wait_for_element_visible('//div[contains(@id, "column-3")]')
    browser.click_and_release(day_tile)
    browser.click('//div[contains(@id, "day-entry-sick-days-div")]')

    # Add a protocol number with correct format (only digits)
    browser.fill('//textarea[contains(@id,"day-entry-protocol-number-input")]', '001234985983400')

    browser.click('//button[contains(text(), "Save")]')

    browser.assert_element('//*[contains(@class, "lucide-stethoscope")]')

    # check the protocol number is saved
    browser.click_and_release(day_tile)
    browser.assert_element(
        '//textarea[contains(@id,"day-entry-protocol-number-input")][contains(text(), "001234985983400")]'
    )


@freeze_time('2025-07-13')
def test_day_entry_modal_accessible_on_timesheet_submitted(
    browser: 'AppTestBrowser', regular_user, freeze_frontend_time
):
    freeze_frontend_time('2025-07-13T00:00:00Z')
    resource = ResourceFactory(user=regular_user)
    TaskFactory(resource=resource)

    TimesheetSubmissionFactory(
        resource=resource, closed=True, period=(datetime.date(2025, 7, 1), datetime.date(2025, 7, 31))
    )

    browser.login_as_user(regular_user)
    browser.click('[href*="timesheet"]')
    day_tile = browser.wait_for_element_visible('//div[contains(@id, "column-3")]')
    browser.click_and_release(day_tile)  # type: ignore
    calendar_input = browser.wait_for_element_visible('//*[contains(@value,"2025-07-04")]')
    assert calendar_input.get_attribute('disabled') == 'true'  # type: ignore
    bank_hour_save = browser.wait_for_element_visible('//input[contains(@id, "save-bank-hour-input")]')
    assert bank_hour_save.get_attribute('disabled') == 'true'  # type: ignore
    bank_hour_use = browser.wait_for_element_visible('//input[contains(@id, "from-bank-hour-input")]')
    assert bank_hour_use.get_attribute('disabled') == 'true'  # type: ignore


@freeze_time('2025-06-25')
@pytest.mark.selenium
@pytest.mark.django_db
def test_timesheet_scheduled_hours_exact_colors(
    browser: 'AppTestBrowser', regular_user, resource_factory, freeze_frontend_time
):
    resource = resource_factory(user=regular_user)
    freeze_frontend_time('2025-06-25T00:00:00Z')
    TaskFactory(
        resource=resource,
        start_date=datetime.date(2025, 6, 1),
        end_date=datetime.date(2025, 6, 30),
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
    browser: 'AppTestBrowser', regular_user, resource_factory, freeze_frontend_time
):
    resource = resource_factory(user=regular_user)
    freeze_frontend_time('2025-06-25T00:00:00Z')
    TaskFactory(
        resource=resource,
        start_date=datetime.date(2025, 6, 1),
        end_date=datetime.date(2025, 6, 30),
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
    browser: 'AppTestBrowser', regular_user, resource_factory, freeze_frontend_time
):
    resource = resource_factory(user=regular_user)
    ContractFactory(resource=resource)
    freeze_frontend_time('2025-06-25T00:00:00Z')
    TaskFactory(
        resource=resource,
        start_date=datetime.date(2025, 6, 1),
        end_date=datetime.date(2025, 6, 30),
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

    browser.click('//*[contains(text(), "More")]')
    browser.fill('//input[@id="daytime-input"]', '13')
    browser.click('//*[contains(text(), "Save")]')
    element_path = (
        '//div[contains(@data-testid, "header-2025-06-24") and contains(@style,'
        f' "{config.MORE_THAN_SCHEDULE_COLOR_DARK_THEME}")]'
    )
    browser.wait_for_element_visible(element_path)


@freeze_time('2025-06-28')
@pytest.mark.selenium
@pytest.mark.django_db
def test_timesheet_non_working_day_more_colors(
    browser: 'AppTestBrowser', regular_user, resource_factory, freeze_frontend_time
):
    """Test adding hours in non-working-day is changing color to MORE_THAN_SCHEDULE_COLOR_DARK_THEME."""
    resource = resource_factory(user=regular_user)
    freeze_frontend_time('2025-06-28T00:00:00Z')
    TaskFactory(
        resource=resource,
        start_date=datetime.date(2025, 6, 1),
        end_date=datetime.date(2025, 6, 30),
    )

    browser.login_as_user(regular_user)
    browser.click('[href*="timesheet"]')

    element = browser.wait_for_element_visible(
        By.XPATH, '//div[@role="button" and starts-with(@id, "Sun Jun 29 2025")]'
    )

    browser.click_and_release(element)

    browser.click('//*[contains(text(), "More")]')
    browser.fill('//input[@id="daytime-input"]', '2')
    browser.click('//*[contains(text(), "Save")]')
    element_path = (
        '//div[contains(@data-testid, "header-2025-06-29") and contains(@style,'
        f' "{config.MORE_THAN_SCHEDULE_COLOR_DARK_THEME}")]'
    )
    browser.wait_for_element_visible(element_path)
