import typing
import pytest

from django.test import override_settings

from testutils.factories import TaskFactory, TimeEntryFactory, ResourceFactory, SpecialLeaveReasonFactory


from freezegun import freeze_time

if typing.TYPE_CHECKING:
    from testutils.selenium import AppTestBrowser

pytestmark = pytest.mark.selenium

@pytest.fixture(autouse=True)
def flag_timesheet():
    with override_settings(FLAGS={'TIMESHEET_ENABLED': [('boolean', True)]}):
        yield

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
    browser.click('//div[contains(@id, "day-entry-leave-radio")]')

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
    browser.click('//div[contains(@id, "day-entry-leave-radio")]')

    browser.fill('//label[contains(text(),"Leave Hours")]/following-sibling::input', '4')
    browser.fill('//label[contains(text(),"Special Leave Hours")]/following-sibling::input', '3')

    browser.click('//select[@name="specialReason"]')
    browser.click(f'//select[@name="specialReason"]/option[text()="{special_leave_reason.title}"]')

    browser.click('//button[contains(text(), "Save")]')

    browser.assert_element(
        '//*[contains(text(), "Invalid time entry for 2025-07-04: '
        'No overtime allowed when logging a leave. Maximum allowed is 8, got 9.00.")]'
    )
