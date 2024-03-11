import re


# Constance
def currency_list_validation(value):
    from django.core.exceptions import ValidationError
    if not re.match(value, r'^[A-Z]{3}(,[A-Z]{3})*$'):
        raise ValidationError('Must be a csv of currency codes')


CONSTANCE_CONFIG = {
    'COUNTRY_GROUPS': ('A, B, C', 'The country grouping list (comma-separated values)'),
    'CURRENCIES': ('GBP,EUR,USD', 'The default currencies to get the rates for', 'currencies')
}

CONSTANCE_BACKEND = 'constance.backends.database.DatabaseBackend'

CONSTANCE_ADDITIONAL_FIELDS = {
    'currencies': [
        'django.forms.CharField', {
            'validators': [currency_list_validation]
        }
    ]
}
