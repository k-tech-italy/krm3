from typing import Iterable
from typing import Any


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
