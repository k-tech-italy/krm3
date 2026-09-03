import typing

import pytest
from freezegun import freeze_time

from testutils.date_utils import _dt
from testutils.factories import (
    DayEntryFactory,
    ResourceFactory,
    SpecialLeaveReasonFactory,
    TimesheetSubmissionFactory,
)

if typing.TYPE_CHECKING:
    from testutils.selenium import AppTestBrowser

pytestmark = pytest.mark.selenium


@freeze_time('2026-03-02')
@pytest.mark.selenium
@pytest.mark.django_db
def test_sick_leave_protocol_number_is_visible_in_report_while_not_submitted(
    browser: 'AppTestBrowser', regular_user, freeze_frontend_time
):
    freeze_frontend_time('2025-03-02T00:00:00Z')
    resource = ResourceFactory(user=regular_user)
    DayEntryFactory(
        day=_dt('2026-03-02'),
        resource=resource,
        due_hours=8,
        is_sick=True,
        protocol_number='12',
    )
    DayEntryFactory(
        day=_dt('2026-03-03'),
        resource=resource,
        due_hours=8,
        is_sick=True,
    )

    browser.login_as_user(regular_user)

    browser.click('[href*="be"]')
    browser.assert_element("//a[text()='Report']")
    browser.click('[href*="report"]')
    browser.assert_element("//td[text()='Sick']")
    browser.assert_element("//td[text()='Sick 12']")


@freeze_time('2026-03-02')
@pytest.mark.selenium
@pytest.mark.django_db
def test_sick_leave_protocol_number_is_visible_in_report_while_submitted(
    browser: 'AppTestBrowser', regular_user, freeze_frontend_time
):
    freeze_frontend_time('2025-03-02T00:00:00Z')
    resource = ResourceFactory(user=regular_user)
    DayEntryFactory(
        day=_dt('2026-03-01'),
        resource=resource,
        due_hours=8,
        is_sick=True,
        protocol_number='12',
    )
    DayEntryFactory(
        day=_dt('2026-03-03'),
        resource=resource,
        due_hours=8,
        is_sick=True,
    )
    TimesheetSubmissionFactory(resource=resource, closed=True, period=(_dt('2026-03-01'), _dt('2026-03-31')))
    browser.login_as_user(regular_user)

    browser.click('[href*="be"]')
    browser.assert_element("//a[text()='Report']")
    browser.click('[href*="report"]')
    browser.assert_element("//td[text()='Sick']")
    browser.assert_element("//td[text()='Sick 12']")


@freeze_time('2026-03-02')
@pytest.mark.selenium
@pytest.mark.django_db
def test_special_leave_reason_is_visible_in_report_while_not_submitted(
    browser: 'AppTestBrowser', regular_user, freeze_frontend_time
):
    freeze_frontend_time('2025-03-02T00:00:00Z')
    resource = ResourceFactory(user=regular_user)
    special_leave_reason = SpecialLeaveReasonFactory()
    DayEntryFactory(
        day=_dt('2026-03-02'),
        due_hours=8,
        special_leave_hours=8,
        special_leave_reason=special_leave_reason,
        resource=resource,
    )
    browser.login_as_user(regular_user)

    browser.click('[href*="be"]')
    browser.assert_element("//a[text()='Report']")
    browser.click('[href*="report"]')
    browser.assert_element(f'//td[text()="Special leave ({special_leave_reason.title})"]')


@freeze_time('2026-03-02')
@pytest.mark.selenium
@pytest.mark.django_db
def test_special_leave_reason_is_visible_in_report_while_submitted(
    browser: 'AppTestBrowser', regular_user, freeze_frontend_time
):
    freeze_frontend_time('2025-03-02T00:00:00Z')
    resource = ResourceFactory(user=regular_user)
    special_leave_reason = SpecialLeaveReasonFactory()
    DayEntryFactory(
        day=_dt('2026-03-02'),
        due_hours=8,
        special_leave_hours=8,
        special_leave_reason=special_leave_reason,
        resource=resource,
    )
    TimesheetSubmissionFactory(resource=resource, closed=True, period=(_dt('2026-03-01'), _dt('2026-03-31')))
    browser.login_as_user(regular_user)

    browser.click('[href*="be"]')
    browser.assert_element("//a[text()='Report']")
    browser.click('[href*="report"]')
    browser.assert_element(f'//td[text()="Special leave ({special_leave_reason.title})"]')
