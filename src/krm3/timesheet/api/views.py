import datetime
from collections.abc import Iterable, Sequence
from typing import TYPE_CHECKING, Any, cast, override

from django.core import exceptions as django_exceptions
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import BooleanField, ExpressionWrapper, Q, QuerySet
from django.utils.translation import gettext as _
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from krm3.core.models import Contract, Resource
from krm3.core.models.timesheets import SpecialLeaveReason, TaskEntry, DayEntry
from krm3.events import Event
from krm3.events.dispatcher import EventDispatcher
from krm3.sentry import capture_exception
from krm3.timesheet.api.serializers import (
    BaseDayEntrySerializer,
    SpecialLeaveReasonSerializer,
    DayEntryCreateSerializer,
    DayEntryReadSerializer,
    TimesheetSerializer,
)
from krm3.timesheet.dto import TimesheetDTO
from krm3.utils.dates import KrmDay, KrmDateRange

if TYPE_CHECKING:
    from krm3.core.models import User
    from krm3.core.models.timesheets import SpecialLeaveReasonQuerySet
    from krm3.core.models.timesheets import TaskEntriesQuerySet

class _TaskEntryCreationFailure(Exception):
    @override
    def __init__(self, time_entry_date: str, messages: Iterable) -> None:
        self.time_entry_date = time_entry_date
        self.messages = messages


class TimesheetAPIViewSet(viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TimesheetSerializer

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='resource_id',
                type=int,
                required=True,
            ),
            OpenApiParameter(
                name='start_date',
                type=str,
                required=True,
            ),
            OpenApiParameter(
                name='end_date',
                type=str,
                required=True,
            ),
        ]
    )
    def list(self, request: Request) -> Response:
        try:
            resource_id = request.query_params['resource_id']
            start_date_iso = request.query_params['start_date']
            end_date_iso = request.query_params['end_date']
        except KeyError:
            return Response(data={'error': 'Required query parameter(s) missing.'}, status=status.HTTP_400_BAD_REQUEST)

        resource = Resource.objects.get(pk=resource_id)
        user = cast('User', request.user)
        if resource.user != request.user and not user.has_any_perm(
            'core.manage_any_timesheet', 'core.view_any_timesheet'
        ):
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

        user = cast('User', request.user)
        timesheet_data = TimesheetDTO(requested_by=user).fetch(resource, start_date, end_date)
        return Response(data=self.get_serializer(timesheet_data).data)


class TaskEntryAPIViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]

    @override
    def get_queryset(self) -> QuerySet[TaskEntry]:
        user = cast('User', self.request.user)
        return TaskEntry.objects.filter_acl(user=user)  # pyright: ignore

    def update(self, request: Request, *args, **kwargs) -> Response:
        if resp := self.check_modify_allowed(request):
            return resp
        return super().update(request, *args, **kwargs)

    def destroy(self, request: Request, *args, **kwargs) -> Response:
        if resp := self.check_modify_allowed(request):
            return resp
        return super().destroy(request, *args, **kwargs)

    @override
    def get_serializer_class(self) -> type[BaseDayEntrySerializer]:
        if self.request.method in ['POST', 'PUT']:
            return DayEntryCreateSerializer
        return DayEntryReadSerializer

    @override
    @extend_schema(
        summary='Create new Time Entry',
        responses={
            201: OpenApiResponse(description='Task assignment created successfully'),
            400: OpenApiResponse(description='Bad request - Invalid data'),
            403: OpenApiResponse(description='Forbidden - Insufficient permissions'),
            404: OpenApiResponse(description='Not found - Task or resource not found'),
        },
        examples=[
            OpenApiExample(
                'Create DayEntry Example',
                value={
                    'task_id': 1,
                    'dates': ['2025-09-01'],
                    'night_shift_hours': 0,
                    'day_shift_hours': 4,
                    'on_call_hours': 0,
                    'travel_hours': 0,
                    'comment': 'some comment',
                    'resource_id': 4,
                },
                request_only=True,
            ),
            OpenApiExample(
                'Multiple Dates DayEntry Example',
                value={
                    'task_id': 2,
                    'dates': ['2025-09-01', '2025-09-02', '2025-09-03'],
                    'night_shift_hours': 8,
                    'day_shift_hours': 0,
                    'on_call_hours': 2,
                    'travel_hours': 1,
                    'comment': 'Task Entry for three days',
                    'resource_id': 5,
                },
                request_only=True,
            ),
        ],
    )
    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        try:
            resource_id = request.data.pop('resource_id')
            resource = Resource.objects.get(pk=resource_id)
            dates =  [KrmDay(d).date for d in set(request.data.pop('dates'))]
            contracts = resource.get_contracts(start_day=dates[0], end_day=dates[-1])

            # normalise keys for the serializer
            request.data['task'] = request.data.pop('task_id', None)
            request.data['resource'] = resource_id
        except (KeyError, ObjectDoesNotExist) as e:
            capture_exception(e)
            if isinstance(e, KeyError):
                return Response(data={'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response(f'Object not found (e)', status=status.HTTP_404_NOT_FOUND)

        if resource.user != request.user and not cast('User', request.user).has_any_perm('core.manage_any_timesheet'):
            return Response(status=status.HTTP_403_FORBIDDEN)

        with transaction.atomic():
            try:
                headers = self._create_time_entries(request, resource, contracts, dates, **request.data)
            except _TaskEntryCreationFailure as e:
                return Response(
                    data={'error': f'Invalid task entry for {e.time_entry_date}: {"; ".join(e.messages)}.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        return Response(status=status.HTTP_201_CREATED, headers=headers)

    def _create_time_entries(
            self,
            request: Request,
            resource: Resource,
            contracts: dict[KrmDateRange, Contract],
            dates: Sequence[str]) -> dict[str, str]:
        """Generate new time entries for the `resource`.

        :param request: the API request
        :param resource: the resource requesting to log hours in the timesheet
        :param dates: the dates for which the resource is logging hours
        :raises _DayEntryCreationFailure: when any time entry fails validation
        :return: the response headers on success
        """
        for dd in dates:
            day_entry = DayEntry.objects.get_or_create()

        # TODO: Provisional fix for #423. Will allow single day edits
        if is_day_entry and len(dates) == 1:
            DayEntry.objects.filter(resource_id=resource.pk, task__isnull=is_day_entry, day__in=dates).delete()

        for formatted_date in dates:
            time_entry_data = request.data.copy()
            time_entry_data.setdefault('date', formatted_date)
            date = datetime.date.fromisoformat(formatted_date)

            if request.data.get('autofill', False):
                contract = Contract.objects.get(
                    resource=resource,
                    period__overlap=(date, date + datetime.timedelta(days=1) if date else None),
                )
                if contract:
                    time_entry_data['day_shift_hours'] = contract.get_remaining_due_hours(
                        date, time_entry_data.get('task')
                    )

            serializer = self.get_serializer(data=time_entry_data, context={'request': request})
            if serializer.is_valid(raise_exception=True):
                try:
                    self.perform_create(serializer)
                except django_exceptions.ValidationError as e:
                    raise _TaskEntryCreationFailure(time_entry_date=formatted_date, messages=e.messages) from e

        if request.data.get('holiday_hours'):
            self.notify_holiday(resource, dates)

        return self.get_success_headers(serializer.data)

    @action(methods=['post'], detail=False)
    def clear(self, request: Request) -> Response:  # noqa: C901
        requested_entry_ids = request.data.get('ids', [])
        if not requested_entry_ids:
            return Response(data={'error': 'No time entry ids provided.'}, status=status.HTTP_400_BAD_REQUEST)
        if not isinstance(requested_entry_ids, list):
            return Response(data={'error': 'Time entry ids must be in a list.'}, status=status.HTTP_400_BAD_REQUEST)

        entries: "TaskEntriesQuerySet" = (
            self.get_queryset()
            .filter(pk__in=requested_entry_ids)
            .annotate(task_is_not_null=ExpressionWrapper(Q(task__isnull=False), output_field=BooleanField()))
            .order_by('task_is_not_null')
        )  # pyright: ignore[reportAssignmentType]

        if not cast('User', request.user).has_any_perm('core.manage_any_timesheet'):
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
            for entry in entries:
                entry.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)

    def check_modify_allowed(self, request: Request) -> Response | None:
        """Check if DayEntry can be modified by user and it is not belonging to a submitted Timesheet."""
        day_entry: DayEntry = self.get_object()
        if day_entry.resource.user != request.user and not request.user.has_perm('core.manage_any_timesheet'):
            return Response(status=status.HTTP_403_FORBIDDEN)
        if day_entry.is_submitted:
            return Response(status=status.HTTP_400_BAD_REQUEST, data={'error': _('Timesheet already submitted.')})
        return None

    def notify_holiday(self, resource: Resource, dates: Iterable[str]) -> None:
        sorted_dates = sorted(dates)
        EventDispatcher().send(
            Event(
                name='holidays',
                payload={
                    'resource': {'name': resource.full_name, 'email': resource.user.email},
                    'start_date': sorted_dates[0],
                    'end_date': sorted_dates[-1],
                },
            )
        )


class DayEntryAPIViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]

    @override
    def get_queryset(self) -> QuerySet[DayEntry]:
        user = cast('User', self.request.user)
        return DayEntry.objects.filter_acl(user=user)  # pyright: ignore


    @override
    def get_serializer_class(self) -> type[BaseDayEntrySerializer]:
        if self.request.method in ['POST', 'PUT']:
            return DayEntryCreateSerializer
        return DayEntryReadSerializer

class SpecialLeaveReasonViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = SpecialLeaveReason.objects.all()
    serializer_class = SpecialLeaveReasonSerializer

    @override
    def list(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        start = datetime.date.fromisoformat(dstr) if (dstr := request.query_params.get('from')) else None
        end = datetime.date.fromisoformat(dstr) if (dstr := request.query_params.get('to')) else None
        try:
            queryset = cast('SpecialLeaveReasonQuerySet', self.get_queryset()).valid_between(start, end)
        except ValueError:
            return Response(
                data={'error': 'Providing only one of "from" and "to" is not allowed. Either provide both or none.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
