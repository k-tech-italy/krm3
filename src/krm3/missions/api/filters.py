"""Filters and ordering for the missions and expenses list endpoints.

Query parameters are sent camelCase (DDR-G-001); `CamelCaseMiddleWare` underscoreizes their names, so the
filters below are declared snake_case. Ordering values are not converted by the middleware, so `OrderingFilter`
exposes them camelCase (`?ordering=-fromDate`).
"""

from django.db.models import Q, QuerySet
from django_filters import rest_framework as filters
from rest_framework.pagination import PageNumberPagination

from krm3.core.models import Expense, Mission


class ListPagination(PageNumberPagination):
    """Default page size as in the settings, overridable with `?pageSize=` up to 100."""

    page_size_query_param = 'page_size'
    max_page_size = 100


class CharInFilter(filters.BaseInFilter, filters.CharFilter):
    """Comma separated values: `?status=DRAFT,SUBMITTED`."""


class NumberInFilter(filters.BaseInFilter, filters.NumberFilter):
    """Comma separated ids: `?resource=1,2`."""


class StableOrderingFilter(filters.OrderingFilter):
    """Append `id` so that pages are stable when the requested ordering has ties."""

    def filter(self, qs: QuerySet, value: list[str] | None) -> QuerySet:
        if not value:
            return qs  # keep the viewset's default ordering
        qs = super().filter(qs, value)
        return qs.order_by(*qs.query.order_by, 'id')


def _words(value: str) -> list[str]:
    return [word for word in value.split() if word]


class MissionFilter(filters.FilterSet):
    status = CharInFilter(field_name='status')
    resource = NumberInFilter(field_name='resource_id')
    # missions overlapping the [date_from, date_to] period
    date_from = filters.DateFilter(field_name='to_date', lookup_expr='gte')
    date_to = filters.DateFilter(field_name='from_date', lookup_expr='lte')
    year = filters.NumberFilter(field_name='year')
    number = filters.NumberFilter(field_name='number')
    search = filters.CharFilter(method='filter_search')

    ordering = StableOrderingFilter(
        fields={
            'id': 'id',
            'number': 'number',
            'year': 'year',
            'status': 'status',
            'from_date': 'fromDate',
            'to_date': 'toDate',
            'title': 'title',
            'resource__last_name': 'resource',
        }
    )

    class Meta:
        model = Mission
        fields = ['status', 'resource', 'date_from', 'date_to', 'year', 'number', 'search']

    def filter_search(self, queryset: QuerySet[Mission], name: str, value: str) -> QuerySet[Mission]:
        """Every word must match one of: title, number, city, country, project, client, resource name."""
        for word in _words(value):
            condition = (
                Q(title__icontains=word)
                | Q(city__name__icontains=word)
                | Q(city__country__name__icontains=word)
                | Q(project__name__icontains=word)
                | Q(project__client__name__icontains=word)
                | Q(resource__first_name__icontains=word)
                | Q(resource__last_name__icontains=word)
            )
            if word.isdigit():
                condition |= Q(number=int(word))
            queryset = queryset.filter(condition)
        return queryset


class ExpenseFilter(filters.FilterSet):
    mission = NumberInFilter(field_name='mission_id')
    resource = NumberInFilter(field_name='mission__resource_id')
    date_from = filters.DateFilter(field_name='day', lookup_expr='gte')
    date_to = filters.DateFilter(field_name='day', lookup_expr='lte')
    category = NumberInFilter(field_name='category_id')
    search = filters.CharFilter(method='filter_search')

    ordering = StableOrderingFilter(
        fields={
            'id': 'id',
            'day': 'day',
            'mission': 'mission',
            'mission__title': 'missionTitle',
            'mission__resource__last_name': 'resource',
            'amount_currency': 'amountCurrency',
            'amount_base': 'amountBase',
        }
    )

    class Meta:
        model = Expense
        fields = ['mission', 'resource', 'date_from', 'date_to', 'category', 'search']

    def filter_search(self, queryset: QuerySet[Expense], name: str, value: str) -> QuerySet[Expense]:
        """Every word must match one of: detail, mission title, category, resource name."""
        for word in _words(value):
            queryset = queryset.filter(
                Q(detail__icontains=word)
                | Q(mission__title__icontains=word)
                | Q(category__title__icontains=word)
                | Q(mission__resource__first_name__icontains=word)
                | Q(mission__resource__last_name__icontains=word)
            )
        return queryset
