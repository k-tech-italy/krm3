from ..environ import env as _env

__all__ = ['FLAGS']

FLAGS = {
    'TRASFERTE_ENABLED': [],
    'TIMESHEET_ENABLED': [],
    'REPORT_ENABLED': [('boolean', True)],
    'CONTACTS_ENABLED': [],
    'DDT_ENABLED': [('boolean', False)],
    'EVENTS_ENABLED': [('boolean', False)],
    'SQL_PERF_MONITOR_ENABLED': [('boolean', _env('DEBUG'))],
}
