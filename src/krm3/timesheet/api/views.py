import datetime
from typing import TYPE_CHECKING, Any, cast, override

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from django.core import exceptions as django_exceptions
from django.db import transaction
from django.db.models import QuerySet
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from krm3.core.models import Resource
from krm3.core.models.timesheets import TimeEntry, TimeEntryQuerySet
from krm3.timesheet import entities
from krm3.timesheet.api.serializers import (
    BaseTimeEntrySerializer,
    TimeEntryReadSerializer,
    TimeEntryCreateSerializer,
    TimesheetSerializer,
)

if TYPE_CHECKING:
    from krm3.core.models import User


class TimesheetAPIViewSet(viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TimesheetSerializer

    @extend_schema(
        description="Fetches a resource's time entries logged within a time interval.",
        parameters=[
            OpenApiParameter(
                name='resource_id',
                location=OpenApiParameter.QUERY,
                type=OpenApiTypes.INT64,
                required=True,
                description='ID of the resource owning the timesheet',
            ),
            OpenApiParameter(
                name='start_date',
                location=OpenApiParameter.QUERY,
                type=OpenApiTypes.DATE,
                required=True,
                description='Start date of the time interval',
            ),
            OpenApiParameter(
                name='end_date',
                location=OpenApiParameter.QUERY,
                type=OpenApiTypes.DATE,
                required=True,
                description='End date of the time interval (inclusive)',
            ),
        ],
    )
    def list(self, request: Request) -> Response:
        try:
            resource_id = request.query_params['resource_id']
            start_date_iso = request.query_params['start_date']
            end_date_iso = request.query_params['end_date']
        except KeyError:
            return Response(data={'error': 'Required query parameter(s) missing.'}, status=status.HTTP_400_BAD_REQUEST)

        resource = Resource.objects.get(pk=resource_id)
        if resource.user != request.user and not cast('User', request.user).can_manage_and_view_any_project():
            return Response(status=status.HTTP_403_FORBIDDEN)

        try:
            start_date = datetime.date.fromisoformat(start_date_iso)
        except (TypeError, ValueError):
            return Response(data={'error': 'Cannot parse start date.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            end_date = datetime.date.fromisoformat(end_date_iso)
        except (TypeError, ValueError):
            return Response(data={'error': 'Cannot parse end date.'}, status=status.HTTP_400_BAD_REQUEST)

        if start_date > end_date:
            return Response(
                data={'error': 'Start date must be earlier than end date.'}, status=status.HTTP_400_BAD_REQUEST
            )

        timesheet = entities.Timesheet(requested_by=cast('User', request.user)).fetch(resource, start_date, end_date)
        serializer = TimesheetSerializer(timesheet)
        return Response(serializer.data)


class TimeEntryAPIViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated]

    @override
    def get_queryset(self) -> QuerySet[TimeEntry]:
        user = cast('User', self.request.user)
        if user.has_any_perm('core.manage_any_timesheet', 'core.view_any_timesheet'):
            return TimeEntry.objects.all()
        return TimeEntry.objects.filter_acl(user=user)  # pyright: ignore

    @override
    def get_serializer_class(self) -> type[BaseTimeEntrySerializer]:
        if self.request.method == 'POST':
            return TimeEntryCreateSerializer
        return TimeEntryReadSerializer

    @extend_schema(
        description='Creates a copy of a time entry for a resource on each of the given dates.',
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'resource_id': {'type': 'int64'},
                    'task_id': {'type': 'int64'},
                    'dates': {
                        'type': 'array',
                        'items': {
                            'type': 'string',
                            'format': 'date',
                        },
                    },
                    'day_shift_hours': {'type': 'number', 'format': 'float', 'multipleOf': 0.25},
                    'sick_hours': {'type': 'number', 'format': 'float', 'multipleOf': 0.25},
                    'holiday_hours': {'type': 'number', 'format': 'float', 'multipleOf': 0.25},
                    'leave_hours': {'type': 'number', 'format': 'float', 'multipleOf': 0.25},
                    'night_shift_hours': {'type': 'number', 'format': 'float', 'multipleOf': 0.25},
                    'on_call_hours': {'type': 'number', 'format': 'float', 'multipleOf': 0.25},
                    'travel_hours': {'type': 'number', 'format': 'float', 'multipleOf': 0.25},
                    'rest_hours': {'type': 'number', 'format': 'float', 'multipleOf': 0.25},
                    'comment': {'type': 'string'},
                },
                'required': ['resource_id', 'task_id', 'dates', 'day_shift_hours'],
            }
        },
    )
    @override
    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        task_id = request.data.pop('task_id', None)

        try:
            resource_id = request.data.pop('resource_id')
            dates = request.data.pop('dates')
        except KeyError as e:
            match str(e):
                case 'resource_id':
                    message = 'Provide both task and resource ID.'
                case 'dates':
                    message = 'Provide at least one date.'
                case _:
                    raise
            return Response(data={'error': message}, status=status.HTTP_400_BAD_REQUEST)

        request.data['task'] = task_id
        request.data['resource'] = resource_id

        try:
            resource = Resource.objects.get(pk=resource_id)
        except Resource.DoesNotExist:
            return Response('Resource not found.', status=status.HTTP_404_NOT_FOUND)

        if resource.user != request.user and not cast('User', request.user).has_any_perm(
            'core.manage_any_project', 'core.manage_any_timesheet'
        ):
            return Response(status=status.HTTP_403_FORBIDDEN)

        if not isinstance(dates, list):
            return Response(data={'error': 'List of dates required.'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            try:
                for date in dates:
                    time_entry_data = request.data.copy()
                    time_entry_data.setdefault('date', date)
                    serializer = self.get_serializer(data=time_entry_data, context={'request': request})
                    if serializer.is_valid(raise_exception=True):
                        self.perform_create(serializer)
            except django_exceptions.ValidationError as e:
                return Response(
                    data={'error': f'Invalid time entry for {date}: {"; ".join(e.messages)}.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        headers = self.get_success_headers(serializer.data)
        return Response(status=status.HTTP_201_CREATED, headers=headers)

    @extend_schema(
        description=(
            'Deletes all time entries whose id is contained in the given array. '
            'If any of the time entries is closed, returns HTTP 400.'
        ),
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'ids': {
                        'type': 'array',
                        'items': {'type': 'integer'},
                    },
                },
                'required': ['ids'],
            }
        },
    )
    @action(methods=['post'], detail=False)
    def clear(self, request: Request) -> Response:
        requested_entry_ids = request.data.get('ids', [])
        if not requested_entry_ids:
            return Response(data={'error': 'No time entry ids provided.'}, status=status.HTTP_400_BAD_REQUEST)
        if not isinstance(requested_entry_ids, list):
            return Response(data={'error': 'Time entry ids must be in a list.'}, status=status.HTTP_400_BAD_REQUEST)

        entries: TimeEntryQuerySet = self.get_queryset().filter(pk__in=requested_entry_ids)  # pyright: ignore[reportAssignmentType]

        if not cast('User', request.user).has_any_perm('core.manage_any_project', 'core.manage_any_timesheet'):
            # since we already ACL-filtered the queryset, we need to
            # know if we have fetched every single one of the objects
            # we requested
            # the problem, though, is that "core.view_any_timesheet"
            # does not grant authorization to delete time entries, so
            # we also need to know who the entries are for!
            fetched_entry_ids = set(entries.values_list('pk', flat=True))
            is_missing_acl_filtered_entries = set(requested_entry_ids) != fetched_entry_ids

            authorized_resource = Resource.objects.get(user=request.user)
            is_user_unauthorized = entries.exclude(resource=authorized_resource).exists()

            if is_missing_acl_filtered_entries or is_user_unauthorized:
                return Response(status=status.HTTP_403_FORBIDDEN)

        if entries.closed().exists():
            return Response(
                data={'error': 'Found closed time entry. Closed time entries are frozen and cannot be deleted.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            entries.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)
