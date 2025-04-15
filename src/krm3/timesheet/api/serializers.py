from collections.abc import Iterable
from typing import Any
from rest_framework import serializers

from krm3.timesheet.models import Task, TimeEntry


class TimeEntrySerializer(serializers.ModelSerializer):
    last_modified = serializers.SerializerMethodField()

    class Meta:
        model = TimeEntry
        fields = (
            'id',
            'date',
            'last_modified',
            'work_hours',
            'sick_hours',
            'holiday_hours',
            'leave_hours',
            'overtime_hours',
            'on_call_hours',
            'travel_hours',
            'rest_hours',
            'state',
            'comment',
        )

    def get_last_modified(self, obj: TimeEntry) -> str:
        return obj.last_modified.isoformat()


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = '__all__'


class TimesheetTaskSerializer(TaskSerializer):
    project_name = serializers.SerializerMethodField()
    time_entries = serializers.SerializerMethodField()

    class Meta(TaskSerializer.Meta):
        fields = (
            'id',
            'title',
            'basket_title',
            'color',
            'start_date',
            'end_date',
            'time_entries',
            'project_name',
        )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self._start_date = kwargs.pop('start_date', None)
        self._end_date = kwargs.pop('end_date', None)
        super().__init__(*args, **kwargs)

    def get_project_name(self, obj: Task) -> str:
        return obj.project.name

    def get_time_entries(self, obj: Task) -> Iterable[dict]:
        time_entries = obj.time_entries.all()
        if self._start_date and self._end_date:
            time_entries = obj.time_entries_between(self._start_date, self._end_date)
        return TimeEntrySerializer(time_entries, many=True).data
