import pytest
from decimal import Decimal as D  # noqa: N817

from krm3.utils.numbers import normal


@pytest.mark.parametrize(
    "value, expected",
    [
        pytest.param(None, '', id='none'),
        pytest.param('any', 'any', id='str'),
        pytest.param(D('3.00'), '3', id='decimal'),
        pytest.param(3.0, '3', id='float'),
    ]
)
def test_normal(value, expected) -> None:
    assert normal(value) == expected
