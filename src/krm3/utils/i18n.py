import datetime

from django.utils.translation import gettext_lazy as _

SHORT_DAYS_OF_WEEK = {
    'Mon': _('Mon'),
    'Tue': _('Tue'),
    'Wed': _('Wed'),
    'Thu': _('Thu'),
    'Fri': _('Fri'),
    'Sat': _('Sat'),
    'Sun': _('Sun'),
}


def short_day_of_week(date: datetime.date) -> str:
    """Return the given date's abbreviated and localized day of the week."""
    dow = date.strftime('%a')
    return str(SHORT_DAYS_OF_WEEK.get(dow, dow))
