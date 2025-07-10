import datetime
from typing import Generator

import pytest
from seleniumbase import config as sb_config
from seleniumbase.core import session_helper

import typing

if typing.TYPE_CHECKING:
    from testutils.selenium import AppSeleniumTC


@pytest.fixture
def browser(live_server, request) -> Generator["AppSeleniumTC", None, None]:
    """SeleniumBase as a pytest fixture.
    Usage example: "def test_one(sb):"
    You may need to use this for tests that use other pytest fixtures."""
    from testutils.selenium import AppSeleniumTC

    if request.cls:
        if sb_config.reuse_class_session:
            the_class = str(request.cls).split(".")[-1].split("'")[0]
            if the_class != sb_config._sb_class:
                session_helper.end_reused_class_session_as_needed()
                sb_config._sb_class = the_class
        request.cls.sb = AppSeleniumTC("base_method")
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
    else:
        sb = AppSeleniumTC("base_method")
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

@pytest.fixture
def freeze_frontend_time(browser):
    def _freeze(iso_date: str):
        dt = datetime.datetime.fromisoformat(iso_date.replace('Z', '+00:00'))
        timestamp_ms = int(dt.timestamp() * 1000)
        browser.driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {
                "source": f"""
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
            }
        )
    return _freeze
