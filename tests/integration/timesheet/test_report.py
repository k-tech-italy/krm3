import datetime
import typing

import pytest
from freezegun import freeze_time
from testutils.factories import ResourceFactory, SpecialLeaveReasonFactory, TaskEntryFactory, TimesheetSubmissionFactory

if typing.TYPE_CHECKING:
    from testutils.selenium import AppTestBrowser

pytestmark = pytest.mark.selenium


@freeze_time('2026-03-02')
@pytest.mark.selenium
@pytest.mark.django_db
def test_sick_leave_protocol_number_is_visible_in_report_while_not_submitted(
    browser: 'AppTestBrowser', regular_user, resource_factory, freeze_frontend_time
):
    freeze_frontend_time('2025-03-02T00:00:00Z')
    resource = ResourceFactory(user=regular_user)
    TaskEntryFactory(
        date=_dt('2026-03-02'), day_shift_hours=0, sick_hours=8, protocol_number='12', resource=resource
    )
    TaskEntryFactory(date=_dt('2026-03-03'), day_shift_hours=0, sick_hours=8, resource=resource)

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
    browser: 'AppTestBrowser', regular_user, resource_factory, freeze_frontend_time
):
    freeze_frontend_time('2025-03-02T00:00:00Z')
    resource = ResourceFactory(user=regular_user)
    TaskEntryFactory(
        date=_dt('2026-03-01'), day_shift_hours=0, sick_hours=8, protocol_number='12', resource=resource
    )
    TaskEntryFactory(date=_dt('2026-03-03'), day_shift_hours=0, sick_hours=8, resource=resource)
    TimesheetSubmissionFactory(
        resource=resource, closed=True, period=(_dt('2026-03-01'), _dt('2026-03-31'))
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
def test_special_leave_reason_is_visible_in_report_while_not_submitted(
    browser: 'AppTestBrowser', regular_user, resource_factory, freeze_frontend_time
):
    freeze_frontend_time('2025-03-02T00:00:00Z')
    resource = ResourceFactory(user=regular_user)
    special_leave_reason = SpecialLeaveReasonFactory()
    TaskEntryFactory(
        date=_dt('2026-03-02'),
        day_shift_hours=0,
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
    browser: 'AppTestBrowser', regular_user, resource_factory, freeze_frontend_time
):
    freeze_frontend_time('2025-03-02T00:00:00Z')
    resource = ResourceFactory(user=regular_user)
    special_leave_reason = SpecialLeaveReasonFactory()
    TaskEntryFactory(
        date=_dt('2026-03-02'),
        day_shift_hours=0,
        special_leave_hours=8,
        special_leave_reason=special_leave_reason,
        resource=resource,
    )
    TimesheetSubmissionFactory(
        resource=resource, closed=True, period=(_dt('2026-03-01'), _dt('2026-03-31'))
    )
    browser.login_as_user(regular_user)

    browser.click('[href*="be"]')
    browser.assert_element("//a[text()='Report']")
    browser.click('[href*="report"]')
    browser.assert_element(f'//td[text()="Special leave ({special_leave_reason.title})"]')
