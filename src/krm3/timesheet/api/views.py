import datetime
from typing import TYPE_CHECKING, Any, cast, override

from django.core import exceptions as django_exceptions
from django.db import transaction
from django.db.models import BooleanField, ExpressionWrapper, Q, QuerySet
from django.utils.translation import gettext as _
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from krm3.core.models import Resource
from krm3.core.models.timesheets import SpecialLeaveReason, TimeEntry, TimeEntryQuerySet
from krm3.timesheet.api.serializers import (
    BaseTimeEntrySerializer,
    SpecialLeaveReasonSerializer,
    TimeEntryCreateSerializer,
    TimeEntryReadSerializer,
    TimesheetSerializer,
)
from krm3.timesheet.utils import get_resource_timesheet

if TYPE_CHECKING:
    from krm3.core.models import User
    from krm3.core.models.timesheets import SpecialLeaveReasonQuerySet


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

        timesheet = get_resource_timesheet(end_date, resource, start_date, user)
        serializer = self.get_serializer(timesheet)

        return Response(serializer.data)


class TimeEntryAPIViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]

    @override
    def get_queryset(self) -> QuerySet[TimeEntry]:
        user = cast('User', self.request.user)
        return TimeEntry.objects.filter_acl(user=user)  # pyright: ignore

    def update(self, request: Request, *args, **kwargs) -> Response:
        if resp := self.check_modify_allowed(request):
            return resp
        return super().update(request, *args, **kwargs)

    def destroy(self, request: Request, *args, **kwargs) -> Response:
        if resp := self.check_modify_allowed(request):
            return resp
        return super().destroy(request, *args, **kwargs)

    @override
    def get_serializer_class(self) -> type[BaseTimeEntrySerializer]:
        if self.request.method in ['POST', 'PUT']:
            return TimeEntryCreateSerializer
        return TimeEntryReadSerializer

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
                'Create TaskEntry Example',
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
                'Multiple Dates TaskEntry Example',
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
    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:  # noqa: C901
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

        try:
            resource = Resource.objects.get(pk=resource_id)
        except Resource.DoesNotExist:
            return Response('Resource not found.', status=status.HTTP_404_NOT_FOUND)

        if resource.user != request.user and not cast('User', request.user).has_any_perm('core.manage_any_timesheet'):
            return Response(status=status.HTTP_403_FORBIDDEN)

        if not isinstance(dates, list):
            return Response(data={'error': 'List of dates required.'}, status=status.HTTP_400_BAD_REQUEST)

        # normalize keys for the serializer
        request.data['task'] = request.data.pop('task_id', None)
        request.data['resource'] = resource_id

        is_day_entry = request.data.get('task', None) is None

        with transaction.atomic():
            try:
                if is_day_entry and len(dates) == 1:  # TODO: Provisional fix for #423. Will allow single day edits
                    TimeEntry.objects.filter(
                        resource_id=resource_id, task__isnull=is_day_entry, date__in=dates
                    ).delete()
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

    @action(methods=['post'], detail=False)
    def clear(self, request: Request) -> Response:  # noqa: C901
        requested_entry_ids = request.data.get('ids', [])
        if not requested_entry_ids:
            return Response(data={'error': 'No time entry ids provided.'}, status=status.HTTP_400_BAD_REQUEST)
        if not isinstance(requested_entry_ids, list):
            return Response(data={'error': 'Time entry ids must be in a list.'}, status=status.HTTP_400_BAD_REQUEST)

        entries: TimeEntryQuerySet = (
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
        """Check if TimeEntry can be modified by user and it is not belonging to a submitted Timesheet."""
        time_entry: TimeEntry = self.get_object()
        if time_entry.resource.user != request.user and not request.user.has_perm('core.manage_any_timesheet'):
            return Response(status=status.HTTP_403_FORBIDDEN)
        if time_entry.is_submitted:
            return Response(status=status.HTTP_400_BAD_REQUEST, data={'error': _('Timesheet already submitted.')})
        return None


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
