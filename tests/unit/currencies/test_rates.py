import datetime
from datetime import date
from decimal import Decimal
from unittest.mock import Mock

import pytest
import responses
from factories import RateFactory


def test_rate_str(db):
    rate = RateFactory()
    assert str(rate) == f'{rate.day:%Y-%m-%d}'


@responses.activate
@pytest.mark.django_db
@pytest.mark.parametrize(
    'initial, force, include, requested, expected', [
        pytest.param(None, False, None, 'EUR,GBP,USD',
                     {'EUR': 0.92172, 'GBP': 0.77373, 'USD': 1}, id='empty'),
        pytest.param({'ABC': 0.9, 'GBP': 1.1}, False, None, 'EUR,USD',
                     {'ABC': 0.9, 'EUR': 0.92172, 'GBP': 1.1, 'USD': 1}, id='existing'),
        pytest.param({'GBP': 1.1}, True, None, 'EUR,GBP,USD',
                     {'EUR': 0.92172, 'GBP': 0.77373, 'USD': 1}, id='force'),
    ]
)
def test_rate_for_day(initial, force, include, requested, expected, mock_rate_provider):
    from krm3.currencies.models import Rate
    assert Rate.objects.count() == 0

    day = date(2022, 5, 7)

    mock_rate_provider(day, requested, {'EUR': 0.92172, 'GBP': 0.77373, 'USD': 1})

    if initial:
        RateFactory(day=day, rates=initial)
    rate = Rate.for_date(day, force=force, include=include)

    assert rate.day == day
    assert rate.rates == expected

    assert Rate.objects.count() == 1
    rate.refresh_from_db()
    assert rate.rates == expected


@responses.activate
@pytest.mark.parametrize(
    'existing, force, include, requested, retrieved, expected', [
        pytest.param(
            {}, False, None, 'EUR,GBP,USD',
            {'EUR': 0.92172, 'GBP': 0.77373, 'USD': 1},
            {'EUR': 0.92172, 'GBP': 0.77373, 'USD': 1},
            id='empty'
        ),
        pytest.param(
            {'KOR': 0.123}, False, None, 'EUR,GBP,USD',
            {'EUR': 0.92172, 'GBP': 0.77373, 'USD': 1, 'KOR': 0.123},
            {'EUR': 0.92172, 'GBP': 0.77373, 'USD': 1, 'KOR': 0.123},
            id='adding'
        ),
        pytest.param(
            {}, False, ['ABC', 'CDE'], 'ABC,CDE,EUR,GBP,USD',
            {'EUR': 0.92172, 'GBP': 0.77373, 'USD': 1, 'ABC': 123, 'CDE': 34.5},
            {'EUR': 0.92172, 'GBP': 0.77373, 'USD': 1, 'ABC': 123, 'CDE': 34.5},
            id='include'
        ),
        pytest.param(  # strangely despite not requesting it we receive GBP, but we ignore it
            {'GBP': 0.99}, False, ['ABC'], 'ABC,EUR,USD',
            {'EUR': 0.92172, 'GBP': 0.77373, 'USD': 1, 'ABC': 123},
            {'EUR': 0.92172, 'GBP': 0.99, 'USD': 1, 'ABC': 123},
            id='existing'
        ),
        pytest.param(
            {'GBP': 0.999}, True, ['ABC'], 'ABC,EUR,GBP,USD',
            {'ABC': 123, 'EUR': 0.92172, 'GBP': 0.77373, 'USD': 1},
            {'ABC': 123, 'EUR': 0.92172, 'GBP': 0.77373, 'USD': 1},
            id='force'
        ),
        pytest.param(
            {'EUR': 0.123, 'GBP': 0.456, 'KOR': 1.1, 'USD': 1}, False, None, 'EUR,GBP,USD',
            {'EUR': 0.92172, 'GBP': 0.77373, 'USD': 1},
            {'EUR': 0.123, 'GBP': 0.456, 'KOR': 1.1, 'USD': 1},
            id='not-needed'
        ),
    ]
)
def test_rate_ensure_rates_ok(existing, force, include, requested, retrieved, expected, mock_rate_provider):
    from krm3.currencies.models import Rate
    rate = Rate(
        day=datetime.datetime.strptime('20231120', '%Y%m%d').date(),
        rates=existing
    )

    mock_rate_provider(rate.day, requested, retrieved)
    rate.ensure_rates(force=force, include=include)

    assert rate.rates == expected


@responses.activate
@pytest.mark.parametrize(
    'from_value, from_currency, to_currency, expected', [
        pytest.param(1, 'USD', 'USD', Decimal('1'), id='usd-usd'),
        pytest.param(1, 'USD', 'EUR', Decimal('0.20'), id='usd-eur'),
        pytest.param(1, 'EUR', 'USD', Decimal('5.0'), id='eur-usd'),
        pytest.param(1, 'USD', 'GBP', Decimal('2'), id='usd-gbp'),
        pytest.param(1, 'GBP', 'EUR', Decimal('0.1'), id='gbp-eur'),
        pytest.param(1, 'EUR', 'GBP', Decimal('10'), id='eur-gbp'),
        pytest.param(1, 'GBP', None, Decimal('0.1'), id='gbp-default'),
    ]
)
def test_rate_convert(from_value, from_currency, to_currency, expected):
    from krm3.currencies.models import Rate
    rate = Rate(date(2022, 5, 7), {'EUR': 0.2, 'GBP': 2, 'USD': 1})

    result = rate.convert(from_value, from_currency, to_currency=to_currency)
    assert result == expected
    assert isinstance(result, Decimal)


@responses.activate
@pytest.mark.parametrize(
    'ensured, force, include, expected', [
        pytest.param(
            {'EUR': 0.92172, 'GBP': 0.77373, 'USD': 1}, False, None,
            {'EUR': 0.2, 'GBP': 2, 'USD': 1},
            id='empty'
        ),
        pytest.param(
            {'EUR': 0.92172, 'GBP': 0.77373, 'USD': 1}, True, None,
            {'EUR': 0.92172, 'GBP': 0.77373, 'USD': 1},
            id='force'
        ),
    ]
)
def test_rate_get_rates(ensured, force, include, expected, monkeypatch):
    monkeypatch.setattr('krm3.currencies.models.currencies.Rate.ensure_rates',
                        mock := Mock(return_value=ensured))
    from krm3.currencies.models import Rate
    rate = Rate(date(2022, 5, 7), {'EUR': 0.2, 'GBP': 2, 'USD': 1})
    if force:
        rate.rates = ensured
    result = rate.get_rates(force=force, include=include)
    assert result == expected
    assert mock.call_count == 1
