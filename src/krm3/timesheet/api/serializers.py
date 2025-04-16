from collections.abc import Iterable
from typing import Any, override
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from krm3.core.models import Task, TimeEntry


class BaseTimeEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = TimeEntry


class TimeEntryReadSerializer(BaseTimeEntrySerializer):
    last_modified = serializers.SerializerMethodField()

    class Meta(BaseTimeEntrySerializer.Meta):
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
        read_only_fields = fields

    def get_last_modified(self, obj: TimeEntry) -> str:
        return obj.last_modified.isoformat()


class TimeEntryCreateSerializer(BaseTimeEntrySerializer):
    class Meta(BaseTimeEntrySerializer.Meta):
        fields = (
            'date',
            'work_hours',
            'sick_hours',
            'holiday_hours',
            'leave_hours',
            'overtime_hours',
            'on_call_hours',
            'travel_hours',
            'rest_hours',
            'comment',
            'task',
            'resource',
        )

    @override
    def validate(self, attrs: Any) -> Any:
        entries_on_same_day = TimeEntry.objects.filter(date=attrs['date'], resource=attrs['resource'])
        total_hours_for_other_entries = sum(entry.total_hours for entry in entries_on_same_day)
        total_hours = (
            attrs['work_hours']
            + attrs.get('overtime_hours', 0)
            + attrs.get('rest_hours', 0)
            + attrs.get('travel_hours', 0)
            + attrs.get('sick_hours', 0)
            + attrs.get('holiday_hours', 0)
            + attrs.get('leave_hours', 0)
        ) + total_hours_for_other_entries

        if total_hours > 24:
            raise serializers.ValidationError(
                _(f'Total hours on {attrs["date"]} ({total_hours}) is over 24 hours'), code='too_much_total_time_logged'
            )

        return super().validate(attrs)


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
        return TimeEntryReadSerializer(time_entries, many=True).data
