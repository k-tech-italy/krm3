import typing
import pytest

from django.test import override_settings

from testutils.factories import TaskFactory, TimeEntryFactory, ResourceFactory


from freezegun import freeze_time

if typing.TYPE_CHECKING:
    from testutils.selenium import AppTestBrowser

pytestmark = pytest.mark.selenium

@pytest.fixture(autouse=True)
def flag_timesheet():
    with override_settings(FLAGS={'TIMESHEET_ENABLED': [('boolean', True)]}):
        yield

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
        'Invalid time entry for 2025-07-04: Cannot both ' 'withdraw from and deposit to bank hours on the same day.'
    )
    actual_error = error_element.text.strip()

    assert actual_error == expected_error, f'❌ Unexpected error message: {actual_error}'


@freeze_time('2025-07-13')
def test_use_more_bank_hours_than_16(browser: 'AppTestBrowser', regular_user, freeze_frontend_time):
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
        day_shift_hours=0,
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

    browser.fill('//input[contains(@id,"from-bank-hour-input")]', '8')
    browser.click('//button[contains(text(), "Save")]')

    error_element = browser.wait_for_element_visible('//p[@id="creation-error-message"]')

    expected_error = (
        'Invalid time entry for 2025-07-09: This transaction would exceed the minimum bank'
        ' balance of -16.0 hours. Current balance: -16.00, attempting to change by: 8.00.'
    )
    actual_error = error_element.text.strip()

    assert actual_error == expected_error, f'❌ Unexpected error message: {actual_error}'


@freeze_time('2025-07-13')
def test_store_more_bank_hours_than_16(browser: 'AppTestBrowser', regular_user, freeze_frontend_time):
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
        day_shift_hours=0,
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
        ' Total hours would become -8.00 which is below scheduled hours (8).'
    )
    actual_error = error_element.text.strip()

    assert actual_error == expected_error, f'❌ Unexpected error message: {actual_error}'
