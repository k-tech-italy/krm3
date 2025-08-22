import json
import re


# Constance
def currency_list_validation(value):
    from django.core.exceptions import ValidationError
    if not re.match(r'^[A-Z]{3}(,[A-Z]{3})*$', value):
        raise ValidationError('Must be a csv of currency codes')


CONSTANCE_CONFIG = {
    'COUNTRY_GROUPS': ('A, B, C', 'The country grouping list (comma-separated values)'),
    'CURRENCIES': ('GBP,EUR,USD', 'The default currencies to get the rates for', 'currencies'),
    'RECENT_DAYS': (60, 'The number of days back to show records by default'),
    'DEFAULT_RESOURCE_SCHEDULE': (
        json.dumps({
            'mon': 8,
            'tue': 8,
            'wed': 8,
            'thu': 8,
            'fri': 8,
            'sat': 0,
            'sun': 0
        }),
        'Minimum hours per day'
    ),
    'BANK_HOURS_DAILY_LIMIT': (8, 'Maximum hours that can be deposited/withdrawn per day', float),
    'BANK_HOURS_UPPER_BOUND': (16, 'Maximum bank hours that can be deposited/withdrawn', float),
    'BANK_HOURS_LOWER_BOUND': (-16, 'Minimum bank hours that can be deposited/withdrawn', float),
}

CONSTANCE_BACKEND = 'constance.backends.database.DatabaseBackend'

CONSTANCE_ADDITIONAL_FIELDS = {
    'currencies': [
        'django.forms.CharField', {
            'validators': [currency_list_validation]
        }
    ]
}
