from typing import Iterable
from typing import Any
from decimal import Decimal as D


def uniq(iterable: Iterable) -> Iterable:
    """Yield unique values from an iterable."""
    seen = set()
    for x in iterable:
        if x in seen:
            continue
        seen.add(x)
        yield x

def parse_emails(value: str) -> list[tuple[Any, Any]]:
    """Parse a list of emails separated by commas."""
    admins = value.split(',')
    return [(a.split('@')[0].strip(), a.strip()) for a in admins]

def format_data(value: int) -> int | None | D:
    return value if value is None or value % 1 != 0 else int(value)
