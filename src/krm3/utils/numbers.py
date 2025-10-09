import typing
from decimal import Decimal as D  # noqa: N817


def normal(val: typing.Any) -> str:  # noqa: N802
    """Normalize a value to string by trying to remove trailing zeroes."""
    if val is None:
        return ''
    if isinstance(val, str):
        return val
    if not isinstance(val, D):
        val = D(val)
    return val.normalize().to_eng_string()


def safe_dec(val: int | float | str | D | None) -> D:
    """Return the val in Decimal format or Decimal(0) is value is None."""
    if val is None:
        return D(0)
    if isinstance(val, D):
        return val
    return D(val)
