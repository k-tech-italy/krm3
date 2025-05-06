from constance import config
from dateutil.relativedelta import relativedelta
from dateutil.utils import today
from django.contrib import admin
from django.utils.translation import gettext_lazy as _


class RecentFilter(admin.SimpleListFilter):
    title = _('Recent')  # Human-readable title of the filter
    parameter_name = 'recent'  # URL query parameter name
    _field = 'to_date'

    def lookups(self, request, model_admin):
        """
        Return a list of tuples.

        The first element in each tuple is the actual value to be used in the URL query,
        and the second element is the human-readable name for the filter option that will appear in the sidebar.
        """
        return (
            ('True', _('Recent')),
            ('False', _('All')),
        )

    def value(self):
        """
        Override the value method to return 'False' as the default.

        (if no value is explicitly set in the query parameters)
        """
        if self.parameter_name in self.used_parameters:
            return self.used_parameters[self.parameter_name]
        return 'True'

    def queryset(self, request, queryset):
        """
        Return the filtered queryset based on the value provided in the query string and retrievable via `self.value()`.
        """
        if self.value() == 'True':
            return queryset.filter(**{f'{self._field}__gte': today() - relativedelta(days=config.RECENT_DAYS)})
        return queryset

    @classmethod
    def factory(cls, field_name: str):
        """Create a filter class for the given field name."""
        return type(f'{cls.__name__}For{field_name.title()}', (cls,), {'_field': field_name})
