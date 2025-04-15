import datetime
from typing import TYPE_CHECKING, Any, cast, override

from django.db.models import QuerySet
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.request import Request
from rest_framework.response import Response

from krm3.core.models import Resource, Task
from krm3.timesheet.api.serializers import TimesheetTaskSerializer

if TYPE_CHECKING:
    from krm3.core.models import User


class TaskAPIViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TimesheetTaskSerializer

    @override
    def get_queryset(self) -> QuerySet[Task]:
        user = cast('User', self.request.user)

        # privileged users can view everyone's tasks
        if user.can_manage_and_view_any_project():
            return Task.objects.all()

        # regular users can only view their own tasks
        resource = Resource.objects.get(user=user)
        return Task.objects.assigned_to(resource=resource)  # pyright: ignore

    @override
    def list(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        try:
            resource_id = request.query_params['resource_id']
            start_date_iso = request.query_params['start_date']
            end_date_iso = request.query_params['end_date']
        except KeyError as e:
            return Response(data={'error': f'Missing mandatory field {e}.'}, status=status.HTTP_400_BAD_REQUEST)

        resource = Resource.objects.get(pk=resource_id)
        if resource.user != request.user and not cast('User', request.user).can_manage_and_view_any_project():
            return Response(status=status.HTTP_403_FORBIDDEN)

        try:
            start_date = datetime.date.fromisoformat(start_date_iso)
        except (TypeError, ValueError) as e:
            return Response(
                data={'error': 'Cannot parse start date.', 'reason': str(e)}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            end_date = datetime.date.fromisoformat(end_date_iso)
        except (TypeError, ValueError) as e:
            return Response(
                data={'error': 'Cannot parse end date.', 'reason': str(e)}, status=status.HTTP_400_BAD_REQUEST
            )

        if start_date > end_date:
            return Response(
                data={'error': 'Start date must be earlier than end date.'}, status=status.HTTP_400_BAD_REQUEST
            )

        tasks = self.get_queryset().active_between(start_date, end_date).assigned_to(resource=resource_id)  # pyright: ignore
        task_data = self.get_serializer(tasks, many=True, start_date=start_date, end_date=end_date).data
        return Response(task_data)
