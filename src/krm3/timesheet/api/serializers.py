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
            'day_shift_hours',
            'sick_hours',
            'holiday_hours',
            'leave_hours',
            'night_shift_hours',
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
            'day_shift_hours',
            'sick_hours',
            'holiday_hours',
            'leave_hours',
            'night_shift_hours',
            'on_call_hours',
            'travel_hours',
            'rest_hours',
            'comment',
            'task',
            'resource',
        )

    def validate_day_shift_hours(self, value: Hours) -> Hours:
        return self._validate_hours(value, field='day_shift_hours')

    def validate_sick_hours(self, value: Hours) -> Hours:
        return self._validate_hours(value, field='sick_hours')

    def validate_holiday_hours(self, value: Hours) -> Hours:
        return self._validate_hours(value, field='holiday_hours')

    def validate_leave_hours(self, value: Hours) -> Hours:
        return self._validate_hours(value, field='leave_hours')

    def validate_night_shift_hours(self, value: Hours) -> Hours:
        return self._validate_hours(value, field='night_shift_hours')

    def validate_on_call_hours(self, value: Hours) -> Hours:
        return self._validate_hours(value, field='on_call_hours')

    def validate_travel_hours(self, value: Hours) -> Hours:
        return self._validate_hours(value, field='travel_hours')

    def validate_rest_hours(self, value: Hours) -> Hours:
        return self._validate_hours(value, field='rest_hours')

    def _validate_hours(self, value: Hours, field: str) -> Hours:
        if Decimal(value) < 0:
            raise serializers.ValidationError(
                _('Hours must not be negative, got {value}.').format(value=value), code=field
            )
        return value

    @override
    def create(self, validated_data: Any) -> TimeEntry:
        date = validated_data.pop('date')
        resource = validated_data.pop('resource')
        task = validated_data.pop('task', None)
        default_hours = {
            'day_shift_hours': 0,
            'night_shift_hours': 0,
            'travel_hours': 0,
            'rest_hours': 0,
            'on_call_hours': 0,
            'sick_hours': 0,
            'holiday_hours': 0,
            'leave_hours': 0,
        }

        entry, _created = TimeEntry.objects.update_or_create(
            date=date,
            resource=resource,
            task=task,
            defaults=default_hours | validated_data,
        )
        return entry


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
