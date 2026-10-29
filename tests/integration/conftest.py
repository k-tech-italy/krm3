import datetime
import time
import typing
from typing import Generator

import pytest
from seleniumbase import config as sb_config
from seleniumbase.core import session_helper

if typing.TYPE_CHECKING:
    from testutils.selenium import AppSeleniumTC


IN_FLIGHT_SESSIONS = (
    "FROM pg_stat_activity WHERE datname = current_database() AND pid <> pg_backend_pid() AND state <> 'idle'"
)


def _wait_for_live_server_requests(attempts: int = 100) -> None:
    """Let the requests still running on the live server end before the test database is flushed.

    A test can end while the browser still has a request in flight (e.g. the save fired by its last click).
    That request's transaction deadlocks with the TRUNCATE of the teardown flush, which then fails with
    "Database test_krm3_gwN couldn't be flushed". Requests still running after ~10s are terminated.
    """
    from django.db import connection  # noqa: PLC0415

    with connection.cursor() as cursor:
        for _ in range(attempts):
            cursor.execute(f'SELECT count(*) {IN_FLIGHT_SESSIONS}')
            if not cursor.fetchone()[0]:
                return
            time.sleep(0.1)
        cursor.execute(f'SELECT pg_terminate_backend(pid) {IN_FLIGHT_SESSIONS}')


@pytest.fixture
def browser(live_server, request) -> Generator['AppSeleniumTC', None, None]:
    """SeleniumBase as a pytest fixture.
    Usage example: "def test_one(sb):"
    You may need to use this for tests that use other pytest fixtures."""
    from testutils.selenium import AppSeleniumTC  # noqa: PLC0415

    if request.cls:
        if sb_config.reuse_class_session:
            the_class = str(request.cls).split('.')[-1].split("'")[0]
            if the_class != sb_config._sb_class:
                session_helper.end_reused_class_session_as_needed()
                sb_config._sb_class = the_class
        request.cls.sb = AppSeleniumTC('base_method')
        request.cls.sb.live_server_url = str(live_server)
        request.cls.sb.setUp()
        request.cls.sb._needs_tearDown = True
        request.cls.sb._using_sb_fixture = True
        request.cls.sb._using_sb_fixture_class = True
        sb_config._sb_node[request.node.nodeid] = request.cls.sb
        yield request.cls.sb
        if request.cls.sb._needs_tearDown:
            request.cls.sb.tearDown()
            request.cls.sb._needs_tearDown = False
        _wait_for_live_server_requests()
    else:
        sb = AppSeleniumTC('base_method')
        sb.live_server_url = str(live_server)
        sb.setUp()
        sb._needs_tearDown = True
        sb._using_sb_fixture = True
        sb._using_sb_fixture_no_class = True
        sb_config._sb_node[request.node.nodeid] = sb
        sb.maximize_window()
        yield sb
        if sb._needs_tearDown:
            sb.tearDown()
            sb._needs_tearDown = False
        _wait_for_live_server_requests()


@pytest.fixture
def freeze_frontend_time(browser):
    def _freeze(iso_date: str):
        dt = datetime.datetime.fromisoformat(iso_date)
        timestamp_ms = int(dt.timestamp() * 1000)
        browser.driver.execute_cdp_cmd(
            'Page.addScriptToEvaluateOnNewDocument',
            {
                'source': f"""
                           const fixedTime = {timestamp_ms};
                           const OriginalDate = Date;
                           class FakeDate extends OriginalDate {{
                               constructor(...args) {{
                                   if (args.length === 0) {{
                                       return new OriginalDate(fixedTime);
                                   }}
                                   return new OriginalDate(...args);
                               }}
                               static now() {{
                                   return fixedTime;
                               }}
                           }}
                           Date = FakeDate;
                       """
            },
        )

    return _freeze
