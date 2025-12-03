from collections.abc import Iterable, Mapping
import datetime
from decimal import Decimal
from typing import Any, override

from django.db import IntegrityError
from django.urls.base import reverse
from django.utils.translation import gettext_lazy as _
from krm3.timesheet.rules import Krm3Day
from psycopg.types.range import DateRange
from rest_framework import exceptions, serializers

from krm3.core.models.contracts import Contract
from krm3.core.models.projects import Task
from krm3.core.models.timesheets import SpecialLeaveReason, TimeEntryQuerySet, TimesheetSubmission, TimeEntry
from krm3.timesheet import dto, utils

type Hours = Decimal | float | int


class BaseTimeEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = TimeEntry


class TimeEntryReadSerializer(BaseTimeEntrySerializer):
    last_modified = serializers.SerializerMethodField()
    task_title = serializers.SerializerMethodField()

    class Meta(BaseTimeEntrySerializer.Meta):
        fields = (
            'id',
            'date',
            'last_modified',
            'day_shift_hours',
            'sick_hours',
            'holiday_hours',
            'leave_hours',
            'special_leave_hours',
            'special_leave_reason',
            'night_shift_hours',
            'on_call_hours',
            'travel_hours',
            'rest_hours',
            'bank_from',
            'bank_to',
            'comment',
            'task',
            'task_title',
            'protocol_number',
        )
        read_only_fields = fields

    def get_last_modified(self, obj: TimeEntry) -> str:
        return obj.last_modified.isoformat()

    def get_task_title(self, obj: TimeEntry) -> str | None:
        if not obj.task:
            return None
        return obj.task.title


class TimeEntryCreateSerializer(BaseTimeEntrySerializer):
    class Meta(BaseTimeEntrySerializer.Meta):
        fields = (
            'date',
            'day_shift_hours',
            'sick_hours',
            'holiday_hours',
            'leave_hours',
            'special_leave_hours',
            'special_leave_reason',
            'night_shift_hours',
            'on_call_hours',
            'travel_hours',
            'rest_hours',
            'bank_from',
            'bank_to',
            'comment',
            'task',
            'resource',
            'protocol_number',
        )

    def validate_day_shift_hours(self, value: Hours) -> Hours:
        return self._validate_hours(value, field='day_shift_hours')

    def validate_sick_hours(self, value: Hours) -> Hours:
        return self._validate_hours(value, field='sick_hours')

    def validate_holiday_hours(self, value: Hours) -> Hours:
        return self._validate_hours(value, field='holiday_hours')

    def validate_leave_hours(self, value: Hours) -> Hours:
        return self._validate_hours(value, field='leave_hours')

    def validate_special_leave_hours(self, value: Hours) -> Hours:
        return self._validate_hours(value, field='special_leave_hours')

    def validate_night_shift_hours(self, value: Hours) -> Hours:
        return self._validate_hours(value, field='night_shift_hours')

    def validate_on_call_hours(self, value: Hours) -> Hours:
        return self._validate_hours(value, field='on_call_hours')

    def validate_travel_hours(self, value: Hours) -> Hours:
        return self._validate_hours(value, field='travel_hours')

    def validate_rest_hours(self, value: Hours) -> Hours:
        return self._validate_hours(value, field='rest_hours')

    def validate_bank_from_hours(self, value: Hours) -> Hours:
        return self._validate_hours(value, field='bank_from')

    def validate_bank_to_hours(self, value: Hours) -> Hours:
        return self._validate_hours(value, field='bank_to')

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
        reason = self._verify_reason_is_valid(validated_data.pop('special_leave_reason', None), date)
        entry, _created = TimeEntry.objects.update_or_create(
            date=date,
            resource=resource,
            task=task,
            special_leave_reason=reason,
            defaults=validated_data,
        )
        return entry

    def _verify_reason_is_valid(
        self, reason: SpecialLeaveReason | None, date: datetime.date
    ) -> SpecialLeaveReason | None:
        if not reason:
            return None

        if reason.is_not_valid_yet(date=date):
            raise serializers.ValidationError(
                _('Reason for special leave is not valid yet: "{value}"').format(value=reason.title)
            )

        if reason.is_expired(date=date):
            raise serializers.ValidationError(
                _('Reason for special leave is expired: "{value}"').format(value=reason.title)
            )

        return reason


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = '__all__'


class TimesheetTaskSerializer(TaskSerializer):
    project_name = serializers.SerializerMethodField()
    client_name = serializers.SerializerMethodField()
    admin_url = serializers.SerializerMethodField()

    class Meta(TaskSerializer.Meta):
        fields = (
            'id',
            'title',
            'basket_title',
            'color',
            'start_date',
            'end_date',
            'project_name',
            'client_name',
            'admin_url',
        )

    def get_client_name(self, obj: Task) -> str:
        return obj.project.client.name

    def get_project_name(self, obj: Task) -> str:
        return obj.project.name

    def get_admin_url(self, obj: Task) -> str:
        """Only allow staff users to get the admin URL."""
        requestor = self.context.get('requestor')
        if requestor and requestor.is_staff:
            return reverse('admin:core_task_change', args=[obj.pk])
        return ''


class TimesheetSerializer(serializers.Serializer):
    tasks = serializers.SerializerMethodField()
    time_entries = TimeEntryReadSerializer(many=True)
    days = serializers.SerializerMethodField()
    schedule = serializers.DictField(child=serializers.IntegerField())
    bank_hours = serializers.DecimalField(max_digits=4, decimal_places=2)
    timesheet_colors = serializers.DictField(child=serializers.CharField())

    def get_tasks(self, timesheet: dto.TimesheetDTO) -> Mapping:
        return TimesheetTaskSerializer(timesheet.tasks, context={'requestor': timesheet.requested_by}, many=True).data

    def get_days(self, timesheet: dto.TimesheetDTO) -> dict[str, dict[str, bool]]:
        days_result = {}

        timesheet_submissions = TimesheetSubmission.objects.filter(resource=timesheet.resource)

        for day in timesheet.days:
            timesheet_submission = timesheet_submissions.filter(period__contains=day.date).first()
            this_day_data = {'closed': timesheet_submission is not None and timesheet_submission.closed}

            contract = timesheet.contracts.filter(period__contains=day.date).first()

            if contract and contract.country_calendar_code:
                this_day_data['hol'] = day.is_holiday(contract.country_calendar_code)
                is_non_working_day = this_day_data['nwd'] = day.is_non_working_day(contract.country_calendar_code)
            else:
                this_day_data['hol'] = day.is_holiday()
                is_non_working_day = this_day_data['nwd'] = day.is_non_working_day()

            meal_voucher_thresholds = contract.meal_voucher if contract else {}
            this_day_data['meal_voucher'] = meal_voucher_thresholds.get(
                'sun' if is_non_working_day else day.day_of_week_short.casefold()
            )

            this_day_time_entries = timesheet.time_entries.filter(date=day.date)
            this_day_data['day_shift_hours'] = float(sum(entry.day_shift_hours for entry in this_day_time_entries))
            this_day_data['night_shift_hours'] = float(sum(entry.night_shift_hours for entry in this_day_time_entries))
            this_day_data['on_call_hours'] = float(sum(entry.on_call_hours for entry in this_day_time_entries))
            this_day_data['travel_hours'] = float(sum(entry.travel_hours for entry in this_day_time_entries))
            this_day_data['holiday_hours'] = float(sum(entry.holiday_hours for entry in this_day_time_entries))
            this_day_data['leave_hours'] = float(sum(entry.leave_hours for entry in this_day_time_entries))
            this_day_data['rest_hours'] = float(sum(entry.rest_hours for entry in this_day_time_entries))
            this_day_data['sick_hours'] = float(sum(entry.sick_hours for entry in this_day_time_entries))

            bank_from = sum(entry.bank_from for entry in this_day_time_entries)
            bank_to = sum(entry.bank_to for entry in this_day_time_entries)
            this_day_data['bank_from'] = float(bank_from)
            this_day_data['bank_to'] = float(bank_to)

            special_leave_hours, special_leave_reason = self._get_special_leave_data(this_day_time_entries)
            this_day_data['special_leave_hours'] = 0.0 if special_leave_hours is None else float(special_leave_hours)
            this_day_data['special_leave_reason'] = special_leave_reason

            due_hours = self._get_due_hours(contract, day)
            overtime = utils.overtime(this_day_time_entries, due_hours)
            this_day_data['overtime'] = 0.0 if overtime is None else float(overtime)

            days_result[str(day.date)] = this_day_data

        return days_result

    def _get_special_leave_data(self, time_entries: TimeEntryQuerySet) -> tuple[Decimal, str] | tuple[None, None]:
        try:
            entry = time_entries.special_leaves().get()
        except (TimeEntry.DoesNotExist, TimeEntry.MultipleObjectsReturned):
            return (None, None)

        return (entry.special_leave_hours, entry.special_leave_reason.title)

    def _get_due_hours(self, contract: Contract | None, day: Krm3Day) -> Decimal:
        if contract:
            return contract.get_due_hours(day.date)
        return Contract.get_default_schedule(day)


class StartEndDateRangeField(serializers.Field):
    def to_representation(self, value: Any) -> tuple[datetime.date, datetime.date] | None:
        if value is None:
            return None
        return (value.lower.isoformat(), value.upper.isoformat())

    def to_internal_value(self, data: Any) -> Any:
        if not isinstance(data, list | tuple):
            raise serializers.ValidationError('Expected a list or a tuple.')

        lower, upper = data

        try:
            lower_date = datetime.date.fromisoformat(lower)
            upper_date = datetime.date.fromisoformat(upper)
        except ValueError:
            raise serializers.ValidationError('Dates must be in ISO format (YYYY-MM-DD).')
        return DateRange(lower_date, upper_date, '[]')


class TimesheetSubmissionSerializer(serializers.ModelSerializer):
    period = StartEndDateRangeField()

    def is_valid(self, *, raise_exception: bool = False) -> bool:
        user = self.context['request'].user
        resource = user.get_resource()
        if user.has_perm('core.manage_any_timesheet') or (
            resource and user.resource.id == self.initial_data['resource']
        ):
            return super().is_valid(raise_exception=raise_exception)
        if raise_exception:
            raise exceptions.PermissionDenied()
        return False

    def save(self, **kwargs) -> None:
        """Handle model constraints and return a 400 bad request if and error occurred."""
        try:
            super().save(**kwargs)
        except IntegrityError as e:
            raise serializers.ValidationError({'error': str(e)})

    class Meta:
        model = TimesheetSubmission
        fields = '__all__'


class SpecialLeaveReasonSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpecialLeaveReason
        fields = '__all__'
