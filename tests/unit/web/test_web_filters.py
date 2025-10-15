import pytest

from krm3.web.templatetags.web_filters import get, is_list, weekday_short_it
from testutils.date_utils import _dt


@pytest.mark.parametrize(
    'val, expected',
    [
        ({}, ''),
        ({'a': 99}, 99),
        ({'b': 99}, ''),
    ]
)
def test_get(val, expected):
    assert get(val, 'a') == expected


@pytest.mark.parametrize(
    'val, expected',
    [
        ({}, False),
        ((), False),
        ([], True),
    ]
)
def test_is_list(val, expected):
    assert is_list(val) is expected

@pytest.mark.parametrize(
    'val, expected',
    [
        (_dt('20251013'), 'Lun'),
        (_dt('20251016'), 'Gio'),
    ]
)
def test_weekday_short_it(val, expected):
    assert weekday_short_it(val) == expected
