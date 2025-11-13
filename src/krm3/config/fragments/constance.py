import json
import re


# Constance
def currency_list_validation(value) -> None:  # noqa: ANN001
    from django.core.exceptions import ValidationError

    if not re.match(r'^[A-Z]{3}(,[A-Z]{3})*$', value):
        raise ValidationError('Must be a csv of currency codes')


CONSTANCE_CONFIG = {
    'COUNTRY_GROUPS': ('A, B, C', 'The country grouping list (comma-separated values)'),
    'CURRENCIES': ('GBP,EUR,USD', 'The default currencies to get the rates for', 'currencies'),
    'RECENT_DAYS': (60, 'The number of days back to show records by default'),
    'DEFAULT_RESOURCE_SCHEDULE': (
        json.dumps({'mon': 8, 'tue': 8, 'wed': 8, 'thu': 8, 'fri': 8, 'sat': 0, 'sun': 0}),
        'Minimum hours per day',
    ),
    'LESS_THAN_SCHEDULE_COLOR_BRIGHT_THEME': (
        '#f66151',
        'color for frontend table header cell when logged hours < schedule',
        'color_field',
    ),
    'EXACT_SCHEDULE_COLOR_BRIGHT_THEME': (
        '#ffffff',
        'color for frontend table header cell when logged hours > schedule',
        'color_field',
    ),
    'MORE_THAN_SCHEDULE_COLOR_BRIGHT_THEME': (
        '#99c1f1',
        'color for frontend table header cell when logged hours > schedule',
        'color_field',
    ),
    'LESS_THAN_SCHEDULE_COLOR_DARK_THEME': (
        '#e01b24',
        'color for frontend table header cell when logged hours < schedule',
        'color_field',
    ),
    'EXACT_SCHEDULE_COLOR_DARK_THEME': (
        '#3d3846',
        'color for frontend table header cell when logged hours == schedule',
        'color_field',
    ),
    'MORE_THAN_SCHEDULE_COLOR_DARK_THEME': (
        '#1a5fb4',
        'color for frontend table header cell when logged hours == schedule',
        'color_field',
    ),
    'BANK_HOURS_UPPER_BOUND': (16.0, 'Maximum bank hours that can be deposited/withdrawn', float),
    'BANK_HOURS_LOWER_BOUND': (-16.0, 'Minimum bank hours that can be deposited/withdrawn', float),
}

CONSTANCE_BACKEND = 'constance.backends.database.DatabaseBackend'

CONSTANCE_ADDITIONAL_FIELDS = {
    'currencies': ['django.forms.CharField', {'validators': [currency_list_validation]}],
    'color_field': [
        'django.forms.fields.CharField',
        {
            'widget': 'django.forms.widgets.TextInput',
            'widget_kwargs': {'attrs': {'type': 'color'}},
        },
    ],
}


class ConstanceTyping:
    COUNTRY_GROUPS: str
    CURRENCIES: str
    LESS_THAN_SCHEDULE_COLOR_BRIGHT_THEME: str
    EXACT_SCHEDULE_COLOR_BRIGHT_THEME: str
    MORE_THAN_SCHEDULE_COLOR_BRIGHT_THEME: str
    LESS_THAN_SCHEDULE_COLOR_DARK_THEME: str
    EXACT_SCHEDULE_COLOR_DARK_THEME: str
    MORE_THAN_SCHEDULE_COLOR_DARK_THEME: str
