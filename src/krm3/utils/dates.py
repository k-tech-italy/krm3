from datetime import datetime


def dt(dat: str) -> datetime.date:
    """Just converts a YYYY-MM-DD string."""
    return datetime.strptime(dat, '%Y-%m-%d').date()
