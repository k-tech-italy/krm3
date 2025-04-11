import datetime
from typing import Any, override
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.request import Request
from rest_framework.response import Response
from krm3.timesheet.api.serializers import TimesheetTaskSerializer
from krm3.timesheet.models import Task


class TaskAPIViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TimesheetTaskSerializer
    queryset = Task.objects.all()

    @override
    def list(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        try:
            resource_id = request.query_params['resource_id']
            start_date_iso = request.query_params['start_date']
            end_date_iso = request.query_params['end_date']
        except KeyError as e:
            return Response(data={'error': f'Mandatory field {e} is missing'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            start_date = datetime.date.fromisoformat(start_date_iso)
            end_date = datetime.date.fromisoformat(end_date_iso)
        except (TypeError, ValueError) as e:
            return Response(
                data={'error': f'Cannot parse as ISO date string: {e}.'}, status=status.HTTP_400_BAD_REQUEST
            )

        if end_date is not None and end_date > start_date:
            return Response(
                data={'error': 'Start date must be earlier than end date'}, status=status.HTTP_400_BAD_REQUEST
            )

        tasks = self.queryset.active_between(start_date, end_date).assigned_to(resource_id=resource_id)  # pyright: ignore
        task_data = self.get_serializer(tasks, many=True)
        return Response(task_data)
