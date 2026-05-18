import pytest
from django.db import connection, DataError
from django.test import override_settings

from krm3.utils.context import request_ctx
from krm3.utils.context_managers import SqlPerfMonitor


@pytest.fixture
def timing_ctx():
    request_ctx.timing = {}
    yield request_ctx.timing
    del request_ctx.timing


@pytest.mark.django_db
@override_settings(FLAGS={'SQL_PERF_MONITOR_ENABLED': [('boolean', False)]})
def test_sql_perf_monitor_disabled(timing_ctx):
    with SqlPerfMonitor(connection) as monitor:
        assert connection.force_debug_cursor is False, 'Disabled monitor should not touch the connection.'
        connection.cursor().execute('SELECT 1')

    assert monitor.enabled is False
    assert timing_ctx == {}, 'Disabled monitor should not record any queries.'


@pytest.mark.django_db
@override_settings(FLAGS={'SQL_PERF_MONITOR_ENABLED': [('boolean', True)]})
def test_sql_perf_monitor_enabled(timing_ctx):
    with SqlPerfMonitor(connection) as monitor:
        connection.cursor().execute('SELECT 1')

    assert monitor.enabled is True
    assert [q['sql'] for q in timing_ctx['sql']] == ['SELECT 1']


@pytest.mark.django_db
@override_settings(FLAGS={'SQL_PERF_MONITOR_ENABLED': [('boolean', True)]})
def test_sql_perf_monitor_skips_recording_on_exception(timing_ctx):
    with pytest.raises(DataError), SqlPerfMonitor(connection):
        connection.cursor().execute('SELECT 1/0')

    assert timing_ctx == {}, 'Queries should not be recorded when the block raises.'
