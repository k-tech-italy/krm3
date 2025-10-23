import datetime
import typing
from collections import OrderedDict

from django import forms
from django.contrib.admin import FieldListFilter
from django.contrib.admin.widgets import AdminDateWidget
from django.db.backends.postgresql.psycopg_any import DateRange
from django.utils.translation import gettext_lazy as _
from rangefilter.filters import DateRangeFilter

from krm3.utils.dates import KrmDay

if typing.TYPE_CHECKING:
    from django.contrib.admin import ModelAdmin
    from django.db.models import Field, Model, QuerySet
    from django.http import HttpRequest


class DateRangeFilterBase(DateRangeFilter):
    """Base class for DateRangeFilter."""

    method: str = None

    def __init__(  # noqa: PLR0913
        self,
        field: 'Field',
        request: 'HttpRequest',
        params: dict,
        model: 'Model',
        model_admin: 'ModelAdmin',
        field_path: str,
    ) -> None:
        self.lookup_kwarg_lower = f'{field_path}__lower'
        self.lookup_kwarg_upper = f'{field_path}__upper'

        FieldListFilter.__init__(self, field, request, params, model, model_admin, field_path)

        self.default_lower, self.default_upper = self._get_default_values(request, model_admin, field_path)
        self.title = self._get_default_title(request, model_admin, field_path)

        self.request = request
        self.model_admin = model_admin
        self.form = self.get_form(request)

    def _get_default_title(self, request: 'HttpRequest', model_admin: 'ModelAdmin', field_path: str) -> str:
        """Return default title."""
        return super()._get_default_title(request, model_admin, field_path) + f' ({self.method})'

    def expected_parameters(self) -> list[str]:
        """Return expected parameters."""
        return [self.lookup_kwarg_lower, self.lookup_kwarg_upper]

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
        date_value_lower = validated_data.get(self.lookup_kwarg_lower, None)
        date_value_upper = validated_data.get(self.lookup_kwarg_upper, None)

        if date_value_lower or date_value_upper:
            if date_value_upper is None:
                date_value_upper = date_value_lower
            elif date_value_lower is None:
                date_value_lower = date_value_upper

        return date_value_lower, date_value_upper

    def _get_form_fields(self) -> dict[str, forms.DateField]:
        return OrderedDict(
            (
                (
                    self.lookup_kwarg_lower,
                    forms.DateField(
                        label='',
                        widget=AdminDateWidget(attrs={'placeholder': _('From date')}),
                        localize=True,
                        required=False,
                        initial=self.default_lower,
                    ),
                ),
                (
                    self.lookup_kwarg_upper,
                    forms.DateField(
                        label='',
                        widget=AdminDateWidget(attrs={'placeholder': _('To date')}),
                        localize=True,
                        required=False,
                        initial=self.default_upper,
                    ),
                ),
            )
        )


DateRangeOverlapFilter = type('DateRangeOverlapFilter', (DateRangeFilterBase,), {'method': 'overlap'})
DateRangeContainedByFilter = type('DateRangeContainedByFilter', (DateRangeFilterBase,), {'method': 'contained_by'})
DateRangeContainsFilter = type('DateRangeContainsFilter', (DateRangeFilterBase,), {'method': 'contains'})
DateRangeFullyLtFilter = type('DateRangeFullyLtFilter', (DateRangeFilterBase,), {'method': 'fully_lt'})
DateRangeFullyGtFilter = type('DateRangeFullyGtFilter', (DateRangeFilterBase,), {'method': 'fully_gt'})
DateRangeNotLtFilter = type('DateRangeNotLtFilter', (DateRangeFilterBase,), {'method': 'not_lt'})
DateRangeNotGtFilter = type('DateRangeNotGtFilter', (DateRangeFilterBase,), {'method': 'not_gt'})
DateRangeAdjacentToFilter = type('DateRangeAdjacentToFilter', (DateRangeFilterBase,), {'method': 'adjacent_to'})

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
