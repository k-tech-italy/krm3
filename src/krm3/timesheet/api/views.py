import datetime
from typing import TYPE_CHECKING, Any, cast, override

from django.core import exceptions as django_exceptions
from django.db import transaction
from django.db.models import QuerySet
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.request import Request
from rest_framework.response import Response

from krm3.core.models import Resource, Task
from krm3.core.models.timesheets import TimeEntry
from krm3.timesheet.api.serializers import (
    BaseTimeEntrySerializer,
    TimeEntryReadSerializer,
    TimeEntryCreateSerializer,
    TimesheetTaskSerializer,
)

if TYPE_CHECKING:
    from krm3.core.models import User


class TaskAPIViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TimesheetTaskSerializer

    @override
    def get_queryset(self) -> QuerySet[Task]:
        user = cast('User', self.request.user)

        if user.can_manage_and_view_any_project():
            return Task.objects.all()
        return Task.objects.filter_acl(user=user)  # pyright: ignore

    @override
    def list(self, request: Request, *args: Any, **kwargs: Any) -> Response:
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

        tasks = self.get_queryset().active_between(start_date, end_date).assigned_to(resource=resource_id)  # pyright: ignore
        task_data = self.get_serializer(tasks, many=True, start_date=start_date, end_date=end_date).data
        return Response(task_data)


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

    @override
    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        try:
            dates = request.data.pop('dates')
        except KeyError:
            return Response(data={'error': 'Provide at least one date.'}, status=status.HTTP_400_BAD_REQUEST)

        if not isinstance(dates, list):
            return Response(
                data={'error': 'List of dates required, but got single date'}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            request.data['task'] = request.data.pop('task_id')
            request.data['resource'] = request.data.pop('resource_id')
        except KeyError:
            return Response(data={'error': 'Provide both task and resource ID.'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            try:
                for date in dates:
                    time_entry_data = request.data.copy()
                    time_entry_data.setdefault('date', date)
                    serializer = self.get_serializer(data=time_entry_data, context={'request': request})
                    if serializer.is_valid(raise_exception=True):
                        self.perform_create(serializer)
            except django_exceptions.ValidationError:
                return Response(data={'error': f'Invalid data entry for {date}.'}, status=status.HTTP_400_BAD_REQUEST)

        headers = self.get_success_headers(serializer.data)
        return Response(status=status.HTTP_201_CREATED, headers=headers)
