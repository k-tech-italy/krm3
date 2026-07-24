from __future__ import annotations

from typing import override, TYPE_CHECKING

from django.db.backends.postgresql.psycopg_any import DateRange  # pyright: ignore
from rangefilter.filters import DateRangeFilter

from krm3.utils.dates import KrmDay

if TYPE_CHECKING:
    import datetime
    from django.db.models import Model, QuerySet
    from django.http import HttpRequest


class DateRangeFilterBase(DateRangeFilter):
    """Base class for DateRangeFilter."""

    method: str = ''

    @override
    def __init__(self, field, request, params, model: type[Model], model_admin, field_path) -> None:  # noqa: ANN001, PLR0913
        super().__init__(field, request, params, model, model_admin, field_path)
        self.title = f'{self.field_path} ({self.method or "none"})'

    @override
    def queryset(self, request: HttpRequest, queryset: QuerySet) -> QuerySet:
        if not self.form.is_valid():
            return queryset

        if not self.form.cleaned_data:
            return queryset

        lower, upper = self._make_query_filter()
        if lower is not None:
            lower = lower.strftime('%Y-%m-%d')
        if upper is not None:
            upper = (KrmDay(upper) + 1).date.strftime('%Y-%m-%d')
        return queryset.filter(**{f'{self.field_path}__{self.method}': DateRange(lower, upper)})

    def _make_query_filter(self) -> tuple[datetime.date, datetime.date] | tuple[None, None]:
        date_value_lower = self.form.cleaned_data.get(self.lookup_kwarg_gte)
        date_value_upper = self.form.cleaned_data.get(self.lookup_kwarg_lte)

        return date_value_lower, date_value_upper


class DateRangeOverlapFilter(DateRangeFilterBase):
    method: str = 'overlap'


class DateRangeContainedByFilter(DateRangeFilterBase):
    method: str = 'contained_by'


class DateRangeContainsFilter(DateRangeFilterBase):
    method: str = 'contains'


class DateRangeFullyLtFilter(DateRangeFilterBase):
    method: str = 'fully_lt'


class DateRangeFullyGtFilter(DateRangeFilterBase):
    method: str = 'fully_gt'


class DateRangeNotLtFilter(DateRangeFilterBase):
    method: str = 'not_lt'


class DateRangeNotGtFilter(DateRangeFilterBase):
    method: str = 'not_gt'


class DateRangeAdjacentToFilter(DateRangeFilterBase):
    method: str = 'adjacent_to'


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
