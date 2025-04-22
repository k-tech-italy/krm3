from decimal import Decimal
from typing import Any, override
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from krm3.core.models import Task, TimeEntry

type Hours = Decimal | float | int


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
            'task',
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

    def validate_work_hours(self, value: Hours) -> Hours:
        return self._validate_hours(value, field='work_hours')

    def validate_sick_hours(self, value: Hours) -> Hours:
        return self._validate_hours(value, field='sick_hours')

    def validate_holiday_hours(self, value: Hours) -> Hours:
        return self._validate_hours(value, field='holiday_hours')

    def validate_leave_hours(self, value: Hours) -> Hours:
        return self._validate_hours(value, field='leave_hours')

    def validate_overtime_hours(self, value: Hours) -> Hours:
        return self._validate_hours(value, field='overtime_hours')

    def validate_on_call_hours(self, value: Hours) -> Hours:
        return self._validate_hours(value, field='on_call_hours')

    def validate_travel_hours(self, value: Hours) -> Hours:
        return self._validate_hours(value, field='travel_hours')

    def validate_rest_hours(self, value: Hours) -> Hours:
        return self._validate_hours(value, field='rest_hours')

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
                _('Total hours on {date} ({total_hours}) is over 24 hours').format(
                    date=attrs['date'], total_hours=total_hours
                ),
                code='too_much_total_time_logged',
            )

        return super().validate(attrs)

    def _validate_hours(self, value: Hours, field: str) -> Hours:
        if Decimal(value) < 0:
            raise serializers.ValidationError(
                _('Hours must not be negative, got {value}.').format(value=value), code=field
            )
        return value


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = '__all__'


class TimesheetTaskSerializer(TaskSerializer):
    project_name = serializers.SerializerMethodField()

    class Meta(TaskSerializer.Meta):
        fields = (
            'id',
            'title',
            'basket_title',
            'color',
            'start_date',
            'end_date',
            'project_name',
        )

    def get_project_name(self, obj: Task) -> str:
        return obj.project.name


class TimesheetSerializer(serializers.Serializer):
    tasks = TimesheetTaskSerializer(many=True)
    time_entries = TimeEntryReadSerializer(many=True)
