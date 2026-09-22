import datetime
import json
from collections.abc import Mapping
from decimal import Decimal

from django.core.exceptions import ValidationError
from ktcalendars import KTDay
from typing import Any, override

from cachetools import cachedmethod
from constance import config
from django.db import IntegrityError, transaction
from django.db.models import QuerySet, Sum
from django.urls.base import reverse
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from psycopg.types.range import DateRange
from rest_framework import exceptions, serializers

from krm3.core.models import TaskEntry, Resource, Task
from krm3.core.models.contracts import Contract
from krm3.core.models.projects import Task
from krm3.core.models.timesheets import (
    DAYTIME_WORK_HOURS_MAX,
    NIGHTTIME_WORK_HOURS_MAX,
    TOTAL_WORK_HOURS_MAX,
    DayEntry,
    SpecialLeaveReason,
    TimesheetSubmission,
)

from krm3.timesheet import dto, utils

# from krm3.timesheet.rules import Krm3Day
# from krm3.utils.dates import KTDay

type Hours = Decimal | float | int


def _model_validation_error_detail(exc: ValidationError) -> dict[str, str | list[str]]:
    if hasattr(exc, 'message_dict'):
        return exc.message_dict
    return {'error': '; '.join(exc.messages)}


class BaseDayEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = DayEntry


class BaseTaskEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskEntry

class TaskEntryReadSerializer(BaseTaskEntrySerializer):
    task_title = serializers.SerializerMethodField()

    class Meta(BaseTaskEntrySerializer.Meta):
        fields = (
            'id',
            'task',
            'task_title',
            'day_entry',
            'day_shift_hours',
            'on_call_hours',
            'travel_hours',
            'night_shift_hours',
            'comment',
            'metadata',
        )
        read_only_fields = fields

    def get_task_title(self, obj: TaskEntry) -> str | None:
        if not obj.task:
            return None
        return obj.task.title


class DayEntryReadSerializer(BaseDayEntrySerializer):
    last_modified = serializers.SerializerMethodField()

    class Meta(BaseDayEntrySerializer.Meta):
        fields = (
            'id',
            'day',
            'last_modified',
            'closed',
            'comment',
            'contract',
            'timesheet',
            'resource',
            'bank',
            'due_hours',
            'travel_hours',
            'day_hours',
            'night_hours',
            'on_call_hours',
            'is_holiday',
            'asked_holiday',
            'leave_hours',
            'special_leave_hours',
            'special_leave_reason',
            'protocol_number',
            'is_sick',
            'rest_hours',
            'overtime_hours',
            'meal_voucher',
        )
        read_only_fields = fields

    def get_last_modified(self, obj: DayEntry) -> str:
        return obj.last_modified.isoformat()


class DayEntryCreateSerializer(BaseDayEntrySerializer):
    dates = serializers.ListField(
        child=serializers.DateField(),
        allow_empty=False,
        required=False,
        write_only=True,
    )

    class Meta(BaseDayEntrySerializer.Meta):
        fields = (
            'day',
            'dates',
            'resource',
            'comment',
            'bank',
            'asked_holiday',
            'leave_hours',
            'special_leave_hours',
            'special_leave_reason',
            'is_sick',
            'protocol_number',
            'rest_hours',
        )
        extra_kwargs = {
            'day': {'required': False},
        }

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """
        Validate holiday, sickness, and special leave data consistency.
        A day cannot be both holiday and sick; protocol is allowed only for sick days;
        special leave hours require a reason.
        Omitted update fields keep their stored values.
        """
        day = attrs.get('day')
        dates = attrs.get('dates')

        if bool(day) == bool(dates):
            raise serializers.ValidationError({
                'error': _('Provide either day or dates, but not both.')
            })

        if dates:
            attrs['dates'] = sorted(set(dates))

        asked_holiday = attrs.get(
            'asked_holiday',
            self.instance.asked_holiday if self.instance else False,
        )
        is_sick = attrs.get(
            'is_sick',
            self.instance.is_sick if self.instance else False,
        )
        protocol_number = attrs.get(
            'protocol_number',
            self.instance.protocol_number if self.instance else None,
        )
        special_leave_hours = attrs.get(
            'special_leave_hours',
            self.instance.special_leave_hours if self.instance else 0,
        )
        special_leave_reason = attrs.get(
            'special_leave_reason',
            self.instance.special_leave_reason if self.instance else None,
        )

        if asked_holiday and is_sick:
            raise serializers.ValidationError({
                'error': _('A day cannot be both holiday and sick.')
            })

        if not is_sick and protocol_number is not None:
            raise serializers.ValidationError({
                'error': _(
                    'Protocol number can only be set for a sick day.'
                )
            })

        if special_leave_hours > 0 and special_leave_reason is None:
            raise serializers.ValidationError({
                'error': _('A special leave reason is required when special leave hours are set.')
            })

        return attrs

    def validate_leave_hours(self, value: Hours) -> Hours:
        return self._validate_hours(value)

    def validate_special_leave_hours(self, value: Hours) -> Hours:
        return self._validate_hours(value)

    def validate_rest_hours(self, value: Hours) -> Hours:
        return self._validate_hours(value)

    def _validate_hours(self, value: Hours) -> Hours:
        if not 0 <= value <= 24:
            raise serializers.ValidationError({
                'error': _('Hours must be between 0 and 24.')
            })
        return value

    @override
    def create(self, validated_data: Any) -> DayEntry:
        day = validated_data['day']
        resource = validated_data['resource']

        if validated_data.get('special_leave_hours', 0) == 0:
            validated_data['special_leave_reason'] = None

        if DayEntry.objects.filter(resource=resource, day=day).exists():
            raise serializers.ValidationError({
                'error': _('A day entry already exists for this resource and date.')
            })

        contract = Contract.objects.by_day(resource, day)
        if contract is None:
            raise serializers.ValidationError({
                'error': _('No valid contract found for this date.')
            })

        reason = validated_data.get('special_leave_reason')
        if reason is not None:
            if reason.is_not_valid_yet(date=day) or reason.is_expired(date=day):
                raise serializers.ValidationError({
                    'error': _('The special leave reason is not valid for this date.')
                })

        timesheet: TimesheetSubmission | None = TimesheetSubmission.objects.filter(
            resource=resource,
            period__contains=day,
        ).first()

        entry = DayEntry(
            **validated_data,
            contract=contract,
            timesheet=timesheet,
            closed=bool(timesheet and timesheet.closed),
            due_hours=contract.get_due_hours(day),
            is_holiday=contract.get_ktday(day).is_holiday,
        )

        try:
            entry.refresh(task_entries=[], drop_existing=False)
            entry.full_clean()
        except ValidationError as exc:
            raise serializers.ValidationError(_model_validation_error_detail(exc)) from exc

        entry.save()
        return entry

    @override
    def update(
            self,
            instance: DayEntry,
            validated_data: dict[str, Any],
    ) -> DayEntry:
        for field, value in validated_data.items():
            setattr(instance, field, value)

        if instance.special_leave_hours == 0:
            instance.special_leave_reason = None

        try:
            instance.verify_bank_hours_against_scheduled_hours()
            instance.verify_bank_hours_restrictions_with_day_entries()

            with transaction.atomic():
                if instance.asked_holiday or instance.is_sick:
                    instance.refresh(task_entries=[])
                else:
                    instance.save()
        except ValidationError as exc:
            raise serializers.ValidationError(_model_validation_error_detail(exc)) from exc

        return instance


class TaskEntryCreateSerializer(BaseTaskEntrySerializer):
    resource_id = serializers.PrimaryKeyRelatedField(
        queryset=Resource.objects.all(),
        write_only=True,
    )
    task_id = serializers.PrimaryKeyRelatedField(
        queryset=Task.objects.all(),
        write_only=True,
    )
    dates = serializers.ListField(
        child=serializers.DateField(),
        allow_empty=False,
        write_only=True,
    )
    autofill = serializers.BooleanField(
        default=False,
        write_only=True,
    )

    class Meta(BaseTaskEntrySerializer.Meta):
        fields = (
            'id',
            'resource_id',
            'task_id',
            'dates',
            'autofill',
            'day_entry',
            'task',
            'day_shift_hours',
            'night_shift_hours',
            'on_call_hours',
            'travel_hours',
            'comment',
            'metadata',
        )
        read_only_fields = ('id','day_entry', 'task')

    def get_fields(self):
        """Select fields according to whether entries are being created or updated."""
        fields = super().get_fields()

        if self.instance is None:
            fields.pop('day_entry')
            fields.pop('task')
        else:
            for name in ('resource_id', 'task_id', 'dates', 'autofill'):
                fields.pop(name)

        return fields

    def validate(self, attrs):
        attrs = super().validate(attrs)

        request = self.context.get('request')
        if request is None:
            raise exceptions.PermissionDenied({
                'error': _('You do not have permission to perform this action.')
            })

        if self.instance is None:
            resource = attrs['resource_id']
        else:
            resource = self.instance.day_entry.resource

        user = request.user

        if (
                self.instance is None
                and attrs['task_id'].resource_id != resource.pk
                and not user.has_perm('core.manage_any_timesheet')
        ):
            raise exceptions.PermissionDenied({
                'error': _('The task is not assigned to the selected resource.')
            })

        if (
                resource.user_id != user.pk
                and not user.has_perm('core.manage_any_timesheet')
        ):
            raise exceptions.PermissionDenied({
                'error': _(
                    'You do not have permission to create task entries '
                    'for this resource.'
                )
            })

        if self.instance is None:
            task = attrs['task_id']
            invalid_dates = sorted({
                day for day in attrs['dates']
                if day not in task.period
            })

            if invalid_dates:
                raise serializers.ValidationError({
                    'error': _(
                        'Cannot create task entries outside the task period.'
                    ).format(
                        dates=', '.join(day.isoformat() for day in invalid_dates)
                    )
                })

        return attrs

    def validate_day_shift_hours(self, value: Hours) -> Hours:
        return self._validate_hours(value, field='day_shift_hours')

    def validate_night_shift_hours(self, value: Hours) -> Hours:
        return self._validate_hours(value, field='night_shift_hours')

    def validate_on_call_hours(self, value: Hours) -> Hours:
        return self._validate_hours(value, field='on_call_hours')

    def validate_travel_hours(self, value: Hours) -> Hours:
        return self._validate_hours(value, field='travel_hours')

    def _validate_hours(self, value: Hours, field: str) -> Hours:
        if Decimal(value) < 0:
            raise serializers.ValidationError(
                {'error': _('Hours must not be negative, got {value}.').format(
                    value=value
                )},
                code=field,
            )

        return value

    def _validate_daily_hour_limits(
            self,
            day_entry: DayEntry,
            candidate_hours: Mapping[str, Hours],
            exclude_task_entry_id: int | None = None,
    ) -> None:
        """Validate the daily hour limits including the candidate task entry."""
        entries = day_entry.taskentry_set.all()

        if exclude_task_entry_id is not None:
            entries = entries.exclude(pk=exclude_task_entry_id)

        existing = entries.aggregate(
            day=Sum('day_shift_hours'),
            night=Sum('night_shift_hours'),
            travel=Sum('travel_hours'),
            on_call=Sum('on_call_hours'),
        )

        day = Decimal(existing['day'] or 0) + Decimal(
            candidate_hours.get('day_shift_hours', 0) or 0
        )
        night = Decimal(existing['night'] or 0) + Decimal(
            candidate_hours.get('night_shift_hours', 0) or 0
        )
        travel = Decimal(existing['travel'] or 0) + Decimal(
            candidate_hours.get('travel_hours', 0) or 0
        )
        on_call = Decimal(existing['on_call'] or 0) + Decimal(
            candidate_hours.get('on_call_hours', 0) or 0
        )

        if day > DAYTIME_WORK_HOURS_MAX:
            raise serializers.ValidationError(
                {'error': _('Maximum 16 daytime hours per day.')}
            )

        if night > NIGHTTIME_WORK_HOURS_MAX:
            raise serializers.ValidationError(
                {'error': _('Maximum 8 nighttime hours per day.')}
            )

        if day + night + travel + on_call > TOTAL_WORK_HOURS_MAX:
            raise serializers.ValidationError(
                {'error': _('Maximum 24 total hours per day.')}
            )

        covered_hours = (
            day_entry.leave_hours
            + day_entry.special_leave_hours
            + day_entry.rest_hours
            + abs(min(day_entry.bank, Decimal('0')))
        )

        if covered_hours > 0:
            maximum_work_hours = max(
                Decimal('0'),
                day_entry.due_hours - covered_hours,
            )

            if day + night + travel > maximum_work_hours:
                raise serializers.ValidationError({
                    'error': _(
                        'Maximum {hours} working hours for this day because '
                        'the remaining due hours are covered by leave, rest, '
                        'or bank hours.'
                    ).format(hours=maximum_work_hours)
                })

    def _get_autofill_hours(self, day_entry: DayEntry) -> Decimal:
        """Return the daytime hours needed to complete the day."""

        logged_hours = (
                day_entry.day_hours
                + day_entry.night_hours
                + day_entry.travel_hours
                + day_entry.leave_hours
                + day_entry.special_leave_hours
                + day_entry.rest_hours
                - day_entry.bank
        )

        return max(
            Decimal('0'),
            day_entry.due_hours - logged_hours,
        )

    def _save_autofill_entry(
            self,
            day_entry: DayEntry,
            task: Task,
            hours: Decimal,
    ) -> TaskEntry:
        """Create a task entry or add hours to the existing one."""

        task_entry = day_entry.taskentry_set.filter(task=task).first()

        if task_entry is None:
            candidate_hours = {
                'day_shift_hours': hours,
            }

            self._validate_daily_hour_limits(
                day_entry=day_entry,
                candidate_hours=candidate_hours,
            )

            return TaskEntry.objects.create(
                day_entry=day_entry,
                task=task,
                day_shift_hours=hours,
            )

        candidate_hours = {
            'day_shift_hours': task_entry.day_shift_hours + hours,
            'night_shift_hours': task_entry.night_shift_hours,
            'travel_hours': task_entry.travel_hours,
            'on_call_hours': task_entry.on_call_hours,
        }

        self._validate_daily_hour_limits(
            day_entry=day_entry,
            candidate_hours=candidate_hours,
            exclude_task_entry_id=task_entry.pk,
        )

        task_entry.day_shift_hours += hours
        task_entry.save(update_fields=['day_shift_hours'])

        return task_entry

    @override
    def create(self, validated_data: Any) -> list[TaskEntry]:
        resource = validated_data.pop('resource_id')
        task = validated_data.pop('task_id')
        dates = sorted(set(validated_data.pop('dates')))
        autofill = validated_data.pop('autofill')

        entries = []

        try:
            with transaction.atomic():
                Resource.objects.select_for_update().get(pk=resource.pk)

                for day in dates:
                    if Contract.objects.by_day(resource, day) is None:
                        raise serializers.ValidationError({
                            'error': _('No valid contract found for {day}.').format(day=day)
                        })

                    try:
                        day_entry = DayEntry.objects.select_for_update().get(
                            resource=resource,
                            day=day,
                        )

                    except DayEntry.DoesNotExist:
                        day_serializer = DayEntryCreateSerializer(
                            data={
                                'day': day,
                                'resource': resource.pk,
                            },
                            context=self.context,
                        )
                        day_serializer.is_valid(raise_exception=True)
                        day_entry = day_serializer.save()

                    submission = TimesheetSubmission.objects.filter(
                        resource=resource,
                        period__contains=day,
                    ).first()

                    day_entry.timesheet = submission
                    day_entry.closed = (
                        submission.closed if submission is not None else False
                    )

                    if day_entry.closed:
                        raise serializers.ValidationError({
                            'error': (
                                'Cannot add task entries to a closed timesheet.'
                            )
                        })

                    entry_data = validated_data.copy()

                    if autofill:
                        hours_to_fill = self._get_autofill_hours(day_entry)

                        if hours_to_fill == 0:
                            continue

                        task_entry = self._save_autofill_entry(
                            day_entry=day_entry,
                            task=task,
                            hours=hours_to_fill,
                        )
                    else:
                        task_entry = day_entry.taskentry_set.filter(task=task).first()
                        if task_entry is None:
                            self._validate_daily_hour_limits(
                                day_entry=day_entry,
                                candidate_hours=entry_data,
                            )
                            task_entry = TaskEntry.objects.create(
                                day_entry=day_entry,
                                task=task,
                                **entry_data,
                            )
                        else:
                            task_entry = self.update(task_entry, entry_data)

                    day_entry.refresh(
                        task_entries=None,
                        drop_existing=False,
                    )

                    entries.append(task_entry)


        except ValidationError as exc:
            raise serializers.ValidationError(_model_validation_error_detail(exc)) from exc

        return entries

    @override
    def update(
            self,
            task_entry: TaskEntry,
            validated_data: Any,
    ) -> TaskEntry:
        hour_fields = (
            'day_shift_hours',
            'night_shift_hours',
            'travel_hours',
            'on_call_hours',
        )

        candidate_hours = {}

        for field in hour_fields:
            if field in validated_data:
                candidate_hours[field] = validated_data[field]
            else:
                candidate_hours[field] = getattr(task_entry, field)

        self._validate_daily_hour_limits(
            day_entry=task_entry.day_entry,
            candidate_hours=candidate_hours,
            exclude_task_entry_id=task_entry.pk,
        )

        task_entry = super().update(task_entry, validated_data)

        task_entry.day_entry.refresh(
            task_entries=None,
            drop_existing=False,
        )

        return task_entry


def _verify_reason_is_valid(
        self, reason: SpecialLeaveReason | None, date: datetime.date
    ) -> SpecialLeaveReason | None:
        if not reason:
            return None

        if reason.is_not_valid_yet(date=date):
            raise serializers.ValidationError({
                'error': _('Reason for special leave is not valid yet: "{value}"').format(
                    value=reason.title
                )
            })

        if reason.is_expired(date=date):
            raise serializers.ValidationError({
                'error': _('Reason for special leave is expired: "{value}"').format(
                    value=reason.title
                )
            })

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
            'basket',
            'color',
            'period',
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
    submitted = serializers.BooleanField()
    tasks = serializers.SerializerMethodField()
    day_entries = DayEntryReadSerializer(many=True)
    days = serializers.SerializerMethodField()
    schedule = serializers.DictField(child=serializers.IntegerField())
    bank_hours = serializers.DecimalField(max_digits=4, decimal_places=2)
    timesheet_colors = serializers.DictField(child=serializers.CharField())
    task_entries = TaskEntryReadSerializer(many=True)

    def get_tasks(self, timesheet: dto.TimesheetDTO) -> Mapping:
        return TimesheetTaskSerializer(timesheet.tasks, context={'requestor': timesheet.requested_by}, many=True).data

    def get_days(self, timesheet: dto.TimesheetDTO) -> dict[str, dict[str, bool]]:
        return list(map(str, timesheet.days))
        # days_result = {}
        #
        # timesheet_submissions = TimesheetSubmission.objects.filter(resource=timesheet.resource)
        #
        # for day_entry in timesheet.day_entries:
        #     days_result[str(day_entry.day)] = {k: getattr(day_entry, k) for k in [
        #         'day_hours',
        #         'night_hours',
        #         'on_call_hours',
        #         'travel_hours',
        #         'leave_hours',
        #         'rest_hours',
        #         'special_leave_hours',
        #         'special_leave_reason',
        #         'bank_from',
        #         'bank_to',
        #         'due_hours',
        #         'is_holiday',
        #         'is_sick',
        #         'asked_holiday',
        #         'protocol_number',
        #     ]
        #     } | {
        #         'overtime': day_entry.overtime_hours
        #     }

        # for day in timesheet.days:
        #     timesheet_submission = timesheet_submissions.filter(period__contains=day.date).first()
        #     this_day_data = {'closed': timesheet_submission is not None and timesheet_submission.closed}
        #
        #     contract = day.contract
        #
        #     if contract and contract.country_calendar_code:
        #         this_day_data['hol'] = day.is_holiday(contract.country_calendar_code)
        #         is_non_working_day = this_day_data['nwd'] = day.is_non_working_day(contract.country_calendar_code)
        #     else:
        #         this_day_data['hol'] = day.is_holiday()
        #         is_non_working_day = this_day_data['nwd'] = day.is_non_working_day()
        #
        #     meal_voucher_thresholds = contract.meal_voucher if contract else {}
        #     this_day_data['meal_voucher'] = meal_voucher_thresholds.get(
        #         'sun' if is_non_working_day else day.day_of_week_short.casefold()
        #     )
        #
        #     this_day_time_entries = timesheet.day_entries.filter(day=day.date)
        #     this_day_data['day_shift_hours'] = float(sum(entry.day_shift_hours for entry in this_day_time_entries))
        #     this_day_data['night_shift_hours'] = float(sum(entry.night_shift_hours for entry in this_day_time_entries))
        #     this_day_data['on_call_hours'] = float(sum(entry.on_call_hours for entry in this_day_time_entries))
        #     this_day_data['travel_hours'] = float(sum(entry.travel_hours for entry in this_day_time_entries))
        #     this_day_data['holiday_hours'] = float(sum(entry.holiday_hours for entry in this_day_time_entries))
        #     this_day_data['leave_hours'] = float(sum(entry.leave_hours for entry in this_day_time_entries))
        #     this_day_data['rest_hours'] = float(sum(entry.rest_hours for entry in this_day_time_entries))
        #     this_day_data['sick_hours'] = float(sum(entry.sick_hours for entry in this_day_time_entries))
        #
        #     bank_from = sum(entry.bank_from for entry in this_day_time_entries)
        #     bank_to = sum(entry.bank_to for entry in this_day_time_entries)
        #     this_day_data['bank_from'] = float(bank_from)
        #     this_day_data['bank_to'] = float(bank_to)
        #
        #     special_leave_hours, special_leave_reason = self._get_special_leave_data(this_day_time_entries)
        #     this_day_data['special_leave_hours'] = 0.0 if special_leave_hours is None else float(special_leave_hours)
        #     this_day_data['special_leave_reason'] = special_leave_reason
        #
        #     due_hours = contract.get_due_hours(day)
        #     overtime = utils.overtime(this_day_time_entries, due_hours)
        #     this_day_data['overtime'] = 0.0 if overtime is None else float(overtime)
        #
        #     days_result[str(day.date)] = this_day_data

        # return days_result

    def _get_special_leave_data(self, day_entries: QuerySet) -> tuple[Decimal, str] | tuple[None, None]:
        entry = day_entries.filter(special_leave_reason__isnull=False).first()
        if entry:
            return (entry.special_leave_hours, entry.special_leave_reason.title)
        return (None, None)

    @cachedmethod(cache=lambda self: self.__dict__.setdefault('_get_default_schedule', {}))
    def _get_default_schedule(self, day: datetime.date | KTDay) -> float:
        day = KTDay(day).day_of_week_short.casefold()
        return json.loads(config.DEFAULT_RESOURCE_SCHEDULE).get(day, 0)


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
