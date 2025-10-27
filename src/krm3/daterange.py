import datetime
import typing
from django.db.backends.postgresql.psycopg_any import DateRange
from rangefilter.filters import DateRangeFilter

from krm3.utils.dates import KrmDay

if typing.TYPE_CHECKING:
    from django.db.models import QuerySet
    from django.http import HttpRequest


class DateRangeFilterBase(DateRangeFilter):
    """Base class for DateRangeFilter."""

    method: str = None

    def __init__(self, field, request, params, model, model_admin, field_path) -> None:  # noqa: ANN001, PLR0913
        super().__init__(field, request, params, model, model_admin, field_path)
        self.title = f'{self.field_path} ({self.method})'

    def queryset(self, request: 'HttpRequest', queryset: 'QuerySet') -> 'QuerySet':
        """Return queryset."""
        if self.form.is_valid():
            validated_data = dict(self.form.cleaned_data.items())
            if validated_data:
                lower, upper = self._make_query_filter(request, validated_data)
                lower = lower.strftime('%Y-%m-%d')
                upper = (KrmDay(upper) + 1).date.strftime('%Y-%m-%d')
                return queryset.filter(**{f'{self.field_path}__{self.method}': DateRange(lower, upper)})
        return queryset

    def _make_query_filter(self, request: 'HttpRequest', validated_data: dict) -> tuple[datetime.date, datetime.date]:
        date_value_lower = validated_data.get(self.lookup_kwarg_gte, None)
        date_value_upper = validated_data.get(self.lookup_kwarg_lte, None)

        if date_value_lower or date_value_upper:
            if date_value_upper is None:
                date_value_upper = date_value_lower
            elif date_value_lower is None:
                date_value_lower = date_value_upper

        return date_value_lower, date_value_upper


class DateRangeOverlapFilter(DateRangeFilterBase):
    method : str = 'overlap'

class DateRangeContainedByFilter(DateRangeFilterBase):
    method : str = 'contained_by'

class DateRangeContainsFilter(DateRangeFilterBase):
    method : str = 'contains'

class DateRangeFullyLtFilter(DateRangeFilterBase):
    method : str = 'fully_lt'

class DateRangeFullyGtFilter(DateRangeFilterBase):
    method : str = 'fully_gt'

class DateRangeNotLtFilter(DateRangeFilterBase):
    method : str = 'not_lt'

class DateRangeNotGtFilter(DateRangeFilterBase):
    method : str = 'not_gt'

class DateRangeAdjacentToFilter(DateRangeFilterBase):
    method : str = 'adjacent_to'

__all__ = [
    'DateRangeOverlapFilter',
    'DateRangeContainedByFilter',
    'DateRangeContainsFilter',
    'DateRangeFullyLtFilter',
    'DateRangeFullyGtFilter',
    'DateRangeNotLtFilter',
    'DateRangeNotGtFilter',
    'DateRangeAdjacentToFilter',
]
