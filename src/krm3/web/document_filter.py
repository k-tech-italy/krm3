"""Document filtering logic for the document management system.

This module provides a clean, maintainable way to apply complex filters to Document querysets.
Filters support nested AND/OR logic and various field-specific operators.

Note on filename filtering:
    Filename filters operate on the basename (filename without path) to match what users see
    in the UI. For example, if the full path is 'documents/2025/11/25/file.pdf',
    the filter will match against 'file.pdf' only.
"""

import datetime
import logging
from typing import Any

from psycopg.types.range import DateRange
from django.db.models import Q, QuerySet

from django_simple_dms.models import Document

logger = logging.getLogger(__name__)


# NOTE: Coverage excluded for DocumentFilter class as it will be moved to django_simple_dms
# in the future. Once migrated, comprehensive tests will be added to the django_simple_dms
# test suite instead of maintaining duplicate tests here.
class DocumentFilter:  # pragma: no cover
    """Applies complex filters to Document queryset.

    Supports nested AND/OR filter groups and field-specific operators:
    - filename: icontains, exact, istartswith, iendswith
    - upload_date: exact, gte, lte, between
    - reference_period: overlaps, contains, contained_by
    - tags: contains_all, contains_any, exact (placeholder for future M2M)

    Example usage:
        queryset = Document.objects.all()
        filter_obj = {"field": "filename", "operator": "icontains", "value": "invoice"}
        filter_instance = DocumentFilter(queryset, filter_obj)
        filtered = filter_instance.apply()
        errors = filter_instance.get_errors()
    """

    def __init__(self, queryset: QuerySet[Document], filter_obj: dict[str, Any]) -> None:
        """Initialize the filter with a queryset and filter specification.

        Args:
            queryset: Base Document queryset to filter
            filter_obj: Filter specification dict (see class docstring for format)

        """
        self.base_queryset = queryset
        self.filter_obj = filter_obj
        self.errors: list[str] = []

    def apply(self) -> QuerySet[Document]:
        """Apply the filter and return the filtered queryset.

        Returns:
            Filtered Document queryset

        """
        return self._apply_filter(self.base_queryset, self.filter_obj)

    def get_errors(self) -> list[str]:
        """Get list of validation errors encountered during filtering.

        Returns:
            List of error messages

        """
        return self.errors

    def _add_error(self, message: str) -> None:
        """Add an error message to the error list.

        Args:
            message: Error message to add

        """
        self.errors.append(message)
        logger.warning(f'Filter validation error: {message}')

    def _apply_filter(
        self, queryset: QuerySet[Document], filter_obj: dict[str, Any]
    ) -> QuerySet[Document]:
        """Recursively apply filter object to queryset.

        Args:
            queryset: Current queryset to filter
            filter_obj: Filter specification

        Returns:
            Filtered queryset

        """
        if not filter_obj:
            return queryset

        # Check if this is a group (has 'op' key) or a single condition
        if 'op' in filter_obj:
            return self._apply_group(queryset, filter_obj)

        return self._apply_condition(queryset, filter_obj)

    def _apply_group(
        self, queryset: QuerySet[Document], filter_obj: dict[str, Any]
    ) -> QuerySet[Document]:
        """Apply a group of conditions with AND/OR logic.

        Args:
            queryset: Current queryset
            filter_obj: Group filter with 'op' and 'conditions' keys

        Returns:
            Filtered queryset

        Raises:
            ValueError: If operator is not 'AND' or 'OR'

        """
        operator = filter_obj.get('op', 'AND')
        conditions = filter_obj.get('conditions', [])

        match operator:
            case 'AND':
                # Apply all conditions sequentially
                for condition in conditions:
                    queryset = self._apply_filter(queryset, condition)
                return queryset
            case 'OR':
                # OR logic - build Q objects from filter conditions directly
                # This avoids multiple subqueries and instead builds a single complex Q object
                q_objects = Q()
                for condition in conditions:
                    q_obj = self._build_q_object(condition)
                    if q_obj:
                        q_objects |= q_obj
                return queryset.filter(q_objects)
            case _:
                raise ValueError(f"Unsupported operator: '{operator}'. Expected 'AND' or 'OR'.")

    def _build_q_object(self, condition: dict[str, Any]) -> Q | None:
        """Build a Q object from a filter condition without executing a query.

        Args:
            condition: Filter condition dictionary

        Returns:
            Q object representing the condition, or None if invalid

        """
        # Handle nested groups recursively
        if 'op' in condition:
            return self._build_group_q_object(condition)

        # Build Q object for single condition
        return self._build_single_condition_q(condition)

    def _build_group_q_object(self, condition: dict[str, Any]) -> Q | None:
        """Build Q object for a group of conditions.

        Raises:
            ValueError: If operator is not 'AND' or 'OR'

        """
        operator = condition.get('op', 'AND')
        sub_conditions = condition.get('conditions', [])

        q_combined = Q()
        for sub_condition in sub_conditions:
            q_obj = self._build_q_object(sub_condition)
            if q_obj:
                match operator:
                    case 'AND':
                        q_combined &= q_obj
                    case 'OR':
                        q_combined |= q_obj
                    case _:
                        raise ValueError(f"Unsupported operator: '{operator}'. Expected 'AND' or 'OR'.")

        return q_combined if q_combined else None

    def _build_single_condition_q(self, condition: dict[str, Any]) -> Q | None:
        """Build Q object for a single filter condition.

        Raises:
            ValueError: If field is not supported

        """
        field = condition.get('field')
        operator = condition.get('operator')
        value = condition.get('value')

        if not field or not operator or value is None:
            return None

        # Route to appropriate field handler
        field_handlers = {
            'filename': self._build_filename_q,
            'upload_date': self._build_upload_date_q,
            'reference_period': self._build_reference_period_q,
            'tags': self._build_tags_q,
        }

        handler = field_handlers.get(field)
        if handler:
            return handler(operator, value)

        raise ValueError(
            f"Unsupported field: '{field}'. "
            f"Expected one of: {', '.join(field_handlers.keys())}"
        )

    @staticmethod
    def _build_filename_q(operator: str, value: str) -> Q:
        """Build Q object for filename filter.

        Note: Filters on the basename (filename without path) to match what users see in the UI.
        The document field stores full paths like 'documents/2025/11/25/file.pdf',
        but we display only 'file.pdf' using the basename filter.

        Raises:
            ValueError: If operator is not supported for filename field

        """
        import re

        match operator:
            case 'icontains':
                # Match the basename containing the value (case-insensitive)
                # Pattern: match if the part after the last slash contains the value
                pattern = rf'[^/]*{re.escape(value)}[^/]*$'
                return Q(document__iregex=pattern)
            case 'exact':
                # Match exact basename (case-insensitive)
                # Pattern: match if the part after the last slash is exactly the value
                pattern = rf'(^|/){re.escape(value)}$'
                return Q(document__iregex=pattern)
            case 'istartswith':
                # Match basename starting with value (case-insensitive)
                # Pattern: match if the part after the last slash starts with the value
                pattern = rf'(^|/){re.escape(value)}[^/]*$'
                return Q(document__iregex=pattern)
            case 'iendswith':
                # Match basename ending with value (case-insensitive)
                # Pattern: match if the part after the last slash ends with the value
                pattern = rf'[^/]*{re.escape(value)}$'
                return Q(document__iendswith=value)  # This one can use simple endswith
            case _:
                raise ValueError(
                    f"Unsupported operator '{operator}' for filename field. "
                    f"Expected one of: icontains, exact, istartswith, iendswith"
                )

    def _build_upload_date_q(self, operator: str, value: str | list[str]) -> Q | None:  # noqa: C901, PLR0911
        """Build Q object for upload_date filter.

        Raises:
            ValueError: If operator is not supported for upload_date field

        """
        try:
            match operator:
                case 'exact':
                    if not isinstance(value, str):
                        return None
                    date_value = datetime.datetime.strptime(value, '%Y-%m-%d').date()
                    return Q(upload_date__date=date_value)
                case 'gte':
                    if not isinstance(value, str):
                        return None
                    date_value = datetime.datetime.strptime(value, '%Y-%m-%d').date()
                    return Q(upload_date__date__gte=date_value)
                case 'lte':
                    if not isinstance(value, str):
                        return None
                    date_value = datetime.datetime.strptime(value, '%Y-%m-%d').date()
                    return Q(upload_date__date__lte=date_value)
                case 'between':
                    if not isinstance(value, list) or len(value) != 2:
                        return None
                    start_date = datetime.datetime.strptime(value[0], '%Y-%m-%d').date()
                    end_date = datetime.datetime.strptime(value[1], '%Y-%m-%d').date()

                    # Validate date range
                    if start_date > end_date:
                        error_msg = (
                            f'Invalid date range for upload date: start date ({value[0]}) '
                            f'must be before or equal to end date ({value[1]})'
                        )
                        self._add_error(error_msg)
                        return None

                    return Q(upload_date__date__gte=start_date, upload_date__date__lte=end_date)
                case _:
                    raise ValueError(
                        f"Unsupported operator '{operator}' for upload_date field. "
                        f"Expected one of: exact, gte, lte, between"
                    )
        except (ValueError, TypeError) as e:
            # Only catch date parsing errors, not our operator validation ValueError
            if "Unsupported operator" in str(e):
                raise
            self._add_error(f'Invalid date format for upload date filter: {value}. Expected format: YYYY-MM-DD')
            return None

    def _build_reference_period_q(self, operator: str, value: list[str]) -> Q | None:
        """Build Q object for reference_period filter.

        Raises:
            ValueError: If operator is not supported for reference_period field

        """
        if not isinstance(value, list) or len(value) != 2:
            return None

        try:
            start_date = datetime.datetime.strptime(value[0], '%Y-%m-%d').date()
            end_date = datetime.datetime.strptime(value[1], '%Y-%m-%d').date()

            # Validate date range
            if start_date > end_date:
                self._add_error(
                    f'Invalid date range for reference period: start date ({value[0]}) '
                    f'must be before or equal to end date ({value[1]})'
                )
                return None

            date_range = DateRange(start_date, end_date, bounds='[]')

            match operator:
                case 'overlaps':
                    return Q(reference_period__overlap=date_range)
                case 'contains':
                    return Q(reference_period__contains=date_range)
                case 'contained_by':
                    return Q(reference_period__contained_by=date_range)
                case _:
                    raise ValueError(
                        f"Unsupported operator '{operator}' for reference_period field. "
                        f"Expected one of: overlaps, contains, contained_by"
                    )
        except (ValueError, TypeError) as e:
            # Only catch date parsing errors, not our operator validation ValueError
            if "Unsupported operator" in str(e):
                raise
            self._add_error(f'Invalid date format for reference period filter: {value}. Expected format: YYYY-MM-DD')
            return None

    @staticmethod
    def _build_tags_q(operator: str, value: list[str]) -> Q | None:
        """Build Q object for tags filter.

        Note: 'exact' operator cannot be represented as a simple Q object
        and will fall back to queryset filtering.

        Raises:
            ValueError: If operator is not supported for tags field

        """
        if not value or not isinstance(value, list):
            return None

        match operator:
            case 'contains_any':
                return Q(tags__title__in=value)
            case 'contains_all':
                # Build chained Q objects for AND logic
                q_combined = Q()
                for tag in value:
                    q_combined &= Q(tags__title=tag)
                return q_combined
            case 'exact':
                # 'exact' operator requires Count aggregation, cannot be done with Q object alone
                # Will fall back to queryset method
                return None
            case _:
                raise ValueError(
                    f"Unsupported operator '{operator}' for tags field. "
                    f"Expected one of: contains_any, contains_all, exact"
                )

    def _apply_condition(
        self, queryset: QuerySet[Document], condition: dict[str, Any]
    ) -> QuerySet[Document]:
        """Apply a single filter condition.

        Args:
            queryset: Current queryset
            condition: Single condition with 'field', 'operator', 'value' keys

        Returns:
            Filtered queryset

        """
        # Try to build a Q object first (more efficient)
        q_obj = self._build_single_condition_q(condition)
        if q_obj:
            return queryset.filter(q_obj)

        # Fall back to special handling for complex filters (e.g., tags 'exact')
        field = condition.get('field')
        operator = condition.get('operator')
        value = condition.get('value')

        if field == 'tags' and operator == 'exact' and isinstance(value, list):
            return self._apply_tags_exact_filter(queryset, value)

        return queryset

    @staticmethod
    def _apply_tags_exact_filter(
        queryset: QuerySet[Document], value: list[str]
    ) -> QuerySet[Document]:
        """Apply exact tags filter - documents must have exactly these tags.

        This requires special handling because it needs Count aggregation,
        which cannot be represented in a simple Q object.

        Args:
            queryset: Current queryset
            value: List of tag title strings

        Returns:
            Filtered queryset with documents having exactly the specified tags

        """
        if not value or not isinstance(value, list):
            return queryset

        from django.db.models import Count

        # Step 1: Find documents that have ALL required tags by filtering sequentially
        # We filter the queryset multiple times (once per tag) to ensure all tags are present
        filtered_qs = queryset
        for tag in value:
            filtered_qs = filtered_qs.filter(tags__title=tag)

        # Step 2: Get the PKs of documents that passed the filter
        matching_pks = list(filtered_qs.values_list('pk', flat=True).distinct())

        if not matching_pks:
            return queryset.none()

        # Step 3: Query fresh from the original queryset to get proper tag counts
        # This ensures the count is not affected by the previous joins
        return queryset.filter(pk__in=matching_pks).annotate(
            tag_count=Count('tags', distinct=True)
        ).filter(tag_count=len(value))
