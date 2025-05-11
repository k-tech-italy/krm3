from typing import Iterable


def uniq(iterable: Iterable) -> Iterable:
    """Yield unique values from an iterable."""
    seen = set()
    for x in iterable:
        if x in seen:
            continue
        seen.add(x)
        yield x
