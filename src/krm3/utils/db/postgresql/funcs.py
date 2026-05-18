# Custom Func class to map to PostgreSQL's intersection operator
from django.contrib.postgres.fields import DateRangeField
from django.db.models import Func


class DateRangeIntersection(Func):
    """Function definition for period intersection."""
    arg_joiner = ' * '
    template = '%(expressions)s'
    output_field = DateRangeField()


class Unnest(Func):
    """Function definition for unnesting array fields."""
    function = 'UNNEST'
