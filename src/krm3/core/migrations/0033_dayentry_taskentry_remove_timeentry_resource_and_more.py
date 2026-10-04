from __future__ import annotations

import datetime
import json
import typing
from decimal import Decimal

import django.contrib.postgres.fields.ranges
import django.db.models.deletion
from constance import config
from django.conf import settings
from django.db import migrations, models
from ktcalendars import KTDay

import krm3.utils.models

if typing.TYPE_CHECKING:
    from django.db.models import Model


def forward_contract_type(apps, schema_editor) -> None:  # noqa: ANN001
    resource_model = apps.get_model('core', 'Resource')

    for resource in resource_model.objects.all():
        contract_type = 'EMPLOYEE' if resource.preferred_in_report else 'CONTRACTOR'
        resource.contract_set.update(contract_type=contract_type)


def backward_contract_type(apps, schema_editor) -> None:  # noqa: ANN001
    resource_model = apps.get_model('core', 'Resource')

    for resource in resource_model.objects.all():
        contract = resource.contract_set.order_by('-period').first()

        if contract is not None:
            resource.preferred_in_report = contract.contract_type == 'EMPLOYEE'
            resource.save(update_fields=['preferred_in_report'])


def forward_contract_base(apps, schema_editor) -> None:  # noqa: ANN001
    country_model = apps.get_model('core', 'Country')
    city_model = apps.get_model('core', 'City')
    contract_model = apps.get_model('core', 'Contract')

    bases = {}
    locations = (
        ('Italy', 'IT', 'Rome', 'RM', ('', 'IT', 'IT-RM')),
        ('United Kingdom', 'GB', 'London', 'ENG', ('GB', 'GB-ENG')),
        ('Poland', 'PL', 'Cracow', None, ('PL',)),
        ('India', 'IN', 'Hyderabad', 'TS', ('IN', 'IN-TS')),
    )
    for country_name, country_code, city_name, subdivision, aliases in locations:
        country, _ = country_model.objects.update_or_create(
            name=country_name,
            defaults={'country_calendar_code': country_code},
        )
        city, _ = city_model.objects.update_or_create(
            name=city_name,
            country=country,
            defaults={'subdivision_code': subdivision},
        )
        for alias in aliases:
            bases[alias] = city

    for contract in contract_model.objects.all():
        country_code = (contract.country_calendar_code or '').strip().upper()

        contract.base_in = bases.get(country_code, bases['IT-RM'])
        contract.save(update_fields=['base_in'])


def backward_contract_base(apps, schema_editor) -> None:  # noqa: ANN001
    contract_model = apps.get_model('core', 'Contract')

    contracts = contract_model.objects.select_related(
        'base_in__country',
    )

    for contract in contracts:
        if contract.base_in is None:
            contract.country_calendar_code = None
        else:
            country_code = contract.base_in.country.country_calendar_code
            subdivision_code = contract.base_in.subdivision_code
            if country_code and subdivision_code:
                country_code = f'{country_code}-{subdivision_code}'
            contract.country_calendar_code = country_code

        contract.save(update_fields=['country_calendar_code'])


def _get_calendar_code(contract) -> str:  # noqa: ANN001
    """Return the holiday calendar code for the contract."""
    base_in = contract.base_in

    if base_in and base_in.country.country_calendar_code:
        country_code = base_in.country.country_calendar_code
        subdivision_code = base_in.subdivision_code

        if subdivision_code:
            return f'{country_code}-{subdivision_code}'

        return country_code

    return settings.HOLIDAYS_CALENDAR


def _is_extra_holiday(
    extra_holiday_model: Model,
    day: datetime.date,
    calendar_code: str,
    database_alias: str,
) -> bool:  # noqa: ANN001
    """Check whether the date is configured as an extra holiday."""
    country_codes = (
        extra_holiday_model.objects.using(database_alias)
        .filter(period__contains=day)
        .values_list('country_codes', flat=True)
    )

    return any(
        calendar_code in codes or (len(calendar_code) > 2 and calendar_code[:2] in codes) for codes in country_codes
    )


MIGRATE_PERIODS_SQL = """
-- Copy the old start and end dates to the new period fields.
UPDATE core_project
SET period = daterange(start_date, end_date, '[]');

UPDATE core_po
SET period = daterange(start_date, end_date, '[]');

UPDATE core_task
SET period = daterange(start_date, end_date, '[]');
"""


RESTORE_LEGACY_PERIOD_DATES_SQL = """
-- Restore the old start and end dates from the period fields on rollback.
UPDATE core_po
SET
    start_date = LOWER(period),
    end_date = CASE
        WHEN UPPER_INF(period) THEN NULL
        ELSE UPPER(period) - 1
    END;

UPDATE core_project
SET
    start_date = LOWER(period),
    end_date = CASE
        WHEN UPPER_INF(period) THEN NULL
        ELSE UPPER(period) - 1
    END;

UPDATE core_task
SET
    start_date = LOWER(period),
    end_date = CASE
        WHEN UPPER_INF(period) THEN NULL
        ELSE UPPER(period) - 1
    END;
"""


CREATE_DAY_ENTRIES_SQL = """
-- Create DayEntry records from the existing TimeEntry data.
WITH days AS (
    SELECT
        time_entry.resource_id,
        time_entry.date,
        MAX(time_entry.last_modified) AS last_modified,
        COALESCE(
            SUM(time_entry.day_shift_hours)
                FILTER (WHERE time_entry.task_id IS NOT NULL),
            0
        ) AS day_hours,
        COALESCE(
            SUM(time_entry.night_shift_hours)
                FILTER (WHERE time_entry.task_id IS NOT NULL),
            0
        ) AS night_hours,
        COALESCE(
            SUM(time_entry.travel_hours)
                FILTER (WHERE time_entry.task_id IS NOT NULL),
            0
        ) AS travel_hours,
        COALESCE(
            SUM(time_entry.on_call_hours)
                FILTER (WHERE time_entry.task_id IS NOT NULL),
            0
        ) AS on_call_hours
    FROM core_timeentry AS time_entry
    GROUP BY
        time_entry.resource_id,
        time_entry.date
),
day_values AS (
    SELECT *
    FROM core_timeentry
    WHERE task_id IS NULL
)
INSERT INTO core_dayentry (
    day,
    last_modified,
    closed,
    comment,
    contract_id,
    timesheet_id,
    resource_id,
    bank,
    due_hours,
    travel_hours,
    day_hours,
    night_hours,
    on_call_hours,
    is_holiday,
    asked_holiday,
    leave_hours,
    special_leave_hours,
    special_leave_reason_id,
    protocol_number,
    is_sick,
    rest_hours,
    overtime_hours,
    meal_voucher
)
SELECT
    days.date,
    days.last_modified,
    COALESCE(timesheet.closed, FALSE),
    day_values.comment,
    contract.id,
    timesheet.id,
    days.resource_id,
    COALESCE(day_values.bank_to, 0)
        - COALESCE(day_values.bank_from, 0),
    0,
    days.travel_hours,
    days.day_hours,
    days.night_hours,
    days.on_call_hours,
    FALSE,
    COALESCE(day_values.holiday_hours, 0) > 0,
    COALESCE(day_values.leave_hours, 0),
    COALESCE(day_values.special_leave_hours, 0),
    day_values.special_leave_reason_id,
    day_values.protocol_number,
    COALESCE(day_values.sick_hours, 0) > 0,
    COALESCE(day_values.rest_hours, 0),
    0,
    0
FROM days
JOIN core_contract AS contract
    ON contract.resource_id = days.resource_id
   AND contract.period @> days.date
LEFT JOIN day_values
    ON day_values.resource_id = days.resource_id
   AND day_values.date = days.date
LEFT JOIN core_timesheetsubmission AS timesheet
    ON timesheet.resource_id = days.resource_id
   AND timesheet.period @> days.date;
"""


CREATE_TASK_ENTRIES_SQL = """
-- Create TaskEntry records from TimeEntries linked to a task.
INSERT INTO core_taskentry (
    day_shift_hours,
    night_shift_hours,
    on_call_hours,
    travel_hours,
    comment,
    metadata,
    day_entry_id,
    task_id
)
SELECT
    time_entry.day_shift_hours,
    time_entry.night_shift_hours,
    time_entry.on_call_hours,
    time_entry.travel_hours,
    time_entry.comment,
    time_entry.metadata,
    day_entry.id,
    time_entry.task_id
FROM core_timeentry AS time_entry
JOIN core_dayentry AS day_entry
    ON day_entry.resource_id = time_entry.resource_id
   AND day_entry.day = time_entry.date
WHERE time_entry.task_id IS NOT NULL;

SELECT setval(
    pg_get_serial_sequence('core_taskentry', 'id'),
    COALESCE(
        (SELECT MAX(task_entry.id) FROM core_taskentry AS task_entry),
        1
    ),
    EXISTS (SELECT 1 FROM core_taskentry)
);
"""


REVERSE_TASK_ENTRIES_SQL = """
-- Restore task-level TimeEntries during rollback.
DELETE FROM core_timeentry;

CREATE TABLE core_day_entry_b AS SELECT * FROM core_dayentry;
CREATE TABLE core_task_entry_b AS SELECT * FROM core_taskentry;


INSERT INTO core_timeentry (
    date,
    last_modified,
    day_shift_hours,
    night_shift_hours,
    on_call_hours,
    travel_hours,
    sick_hours,
    holiday_hours,
    leave_hours,
    rest_hours,
    special_leave_hours,
    bank_from,
    bank_to,
    comment,
    metadata,
    protocol_number,
    resource_id,
    task_id,
    special_leave_reason_id,
    timesheet_id
)
SELECT
    day_entry.day,
    day_entry.last_modified,
    COALESCE(task_entry.day_shift_hours, 0.0),
    COALESCE(task_entry.night_shift_hours, 0.0),
    COALESCE(task_entry.on_call_hours, 0.0),
    COALESCE(task_entry.travel_hours, 0.0),
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    task_entry.comment,
    coalesce(task_entry.metadata, '{}'),
    NULL,
    day_entry.resource_id,
    task_entry.task_id,
    NULL::bigint,
    day_entry.timesheet_id
FROM core_taskentry AS task_entry
RIGHT JOIN core_dayentry AS day_entry
    ON day_entry.id = task_entry.day_entry_id;

SELECT setval(
    pg_get_serial_sequence('core_timeentry', 'id'),
    COALESCE(
        (SELECT MAX(time_entry.id) FROM core_timeentry AS time_entry),
        1
    ),
    EXISTS (SELECT 1 FROM core_timeentry)
);

DELETE FROM core_taskentry;
"""


REVERSE_DAY_ENTRIES_SQL = """
-- Restore day-level TimeEntries during rollback.
INSERT INTO core_timeentry (
    date,
    last_modified,
    day_shift_hours,
    night_shift_hours,
    on_call_hours,
    travel_hours,
    sick_hours,
    holiday_hours,
    leave_hours,
    rest_hours,
    special_leave_hours,
    bank_from,
    bank_to,
    comment,
    metadata,
    protocol_number,
    resource_id,
    task_id,
    special_leave_reason_id,
    timesheet_id
)
SELECT
    day_entry.day,
    day_entry.last_modified,
    0,
    0,
    0,
    0,
    CASE
        WHEN day_entry.is_sick THEN day_entry.due_hours
        ELSE 0
    END,
    CASE
        WHEN day_entry.asked_holiday THEN day_entry.due_hours
        ELSE 0
    END,
    day_entry.leave_hours,
    day_entry.rest_hours,
    day_entry.special_leave_hours,
    GREATEST(-day_entry.bank, 0),
    GREATEST(day_entry.bank, 0),
    day_entry.comment,
    '{}'::jsonb,
    day_entry.protocol_number,
    day_entry.resource_id,
    NULL,
    day_entry.special_leave_reason_id,
    day_entry.timesheet_id
FROM core_dayentry AS day_entry
WHERE
    day_entry.bank <> 0
    OR day_entry.asked_holiday
    OR day_entry.leave_hours <> 0
    OR day_entry.special_leave_hours <> 0
    OR day_entry.special_leave_reason_id IS NOT NULL
    OR day_entry.protocol_number IS NOT NULL
    OR day_entry.is_sick
    OR day_entry.rest_hours <> 0
    OR day_entry.comment IS NOT NULL;


INSERT INTO core_timeentry (
    date,
    last_modified,
    day_shift_hours,
    night_shift_hours,
    on_call_hours,
    travel_hours,
    sick_hours,
    holiday_hours,
    leave_hours,
    rest_hours,
    special_leave_hours,
    bank_from,
    bank_to,
    comment,
    metadata,
    protocol_number,
    resource_id,
    task_id,
    special_leave_reason_id,
    timesheet_id
)
SELECT
    day,
    last_modified,
    0,
    0,
    0,
    0,
    0,
    COALESCE((working_schedule ->> TO_CHAR(day, 'dy'))::integer, 8),
    0,
    0,
    0,
    0,
    0,
    core_dayentry.comment,
    '{}'::jsonb,
    NULL,
    core_dayentry.resource_id,
    NULL,
    NULL::bigint,
    timesheet_id
FROM core_dayentry
JOIN core_contract
    ON core_contract.id=contract_id
WHERE is_holiday=true and asked_holiday = true;

DELETE FROM core_timeentry AS te
WHERE te.holiday_hours = 0
  AND task_id is NULL
  AND EXISTS (
      SELECT 1
      FROM core_timeentry AS h
      WHERE h.resource_id = te.resource_id
        AND h.date = te.date
        AND h.holiday_hours > 0
  );

DELETE FROM core_timeentry
WHERE
sick_hours=0
AND holiday_hours=0
AND leave_hours=0
AND on_call_hours=0
AND travel_hours=0
AND rest_hours=0
AND coalesce(comment, '') = ''
AND metadata='{}'
AND day_shift_hours=0
and night_shift_hours=0
and special_leave_hours=0
and special_leave_reason_id is null
and bank_from=0
and bank_to=0;

DELETE FROM core_dayentry;
"""


def recalculate_day_entries(apps, schema_editor) -> None:  # noqa: ANN001
    """Calculate holidays, due hours, overtime, and meal vouchers after the SQL migration."""
    DayEntry = apps.get_model('core', 'DayEntry')
    ExtraHoliday = apps.get_model('core', 'ExtraHoliday')

    database_alias = schema_editor.connection.alias
    default_schedule = json.loads(config.DEFAULT_RESOURCE_SCHEDULE)

    day_entries = list(
        DayEntry.objects.using(database_alias)
        .select_related(
            'contract',
            'contract__base_in',
            'contract__base_in__country',
        )
        .all()
    )

    for day_entry in day_entries:
        contract = day_entry.contract
        calendar_code = _get_calendar_code(contract)
        calendar_day = KTDay(
            day_entry.day,
            cal_country_code=calendar_code,
        )
        weekday = calendar_day.day_of_week_short.casefold()

        is_extra_holiday = _is_extra_holiday(
            ExtraHoliday,
            day_entry.day,
            calendar_code,
            database_alias,
        )
        day_entry.is_holiday = calendar_day.is_holiday or is_extra_holiday

        working_schedule = contract.working_schedule or default_schedule
        day_entry.due_hours = Decimal(0) if day_entry.is_holiday else Decimal(str(working_schedule[weekday]))

        worked_hours = Decimal(day_entry.day_hours) + Decimal(day_entry.night_hours) + Decimal(day_entry.travel_hours)

        if contract.overtime:
            overtime = worked_hours - day_entry.due_hours
            day_entry.overtime_hours = max(
                overtime,
                Decimal(0),
            )
        else:
            day_entry.overtime_hours = Decimal(0)

        day_entry.meal_voucher = 0

        if contract.meal_voucher:
            meal_threshold = Decimal(str(contract.meal_voucher[weekday]))

            if meal_threshold:
                bank_withdrawal = max(
                    -Decimal(day_entry.bank),
                    Decimal(0),
                )
                eligible_hours = worked_hours + bank_withdrawal
                day_entry.meal_voucher = int(eligible_hours >= meal_threshold)

    DayEntry.objects.using(database_alias).bulk_update(
        day_entries,
        fields=[
            'is_holiday',
            'due_hours',
            'overtime_hours',
            'meal_voucher',
        ],
        batch_size=1000,
    )


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0032_contact_title_alter_contact_job_title_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='contract',
            name='contract_type',
            field=models.CharField(
                choices=[
                    ('EMPLOYEE', 'Employee'),
                    ('CONTRACTOR', 'Contractor'),
                    ('OTHER', 'Other'),
                ],
                default='EMPLOYEE',
                max_length=10,
            ),
        ),
        migrations.RunPython(forward_contract_type, backward_contract_type),
        migrations.AddConstraint(
            model_name='contract',
            constraint=models.CheckConstraint(
                name='valid_contract_type',
                condition=models.Q(
                    contract_type__in=[
                        'EMPLOYEE',
                        'CONTRACTOR',
                        'OTHER',
                    ],
                ),
            ),
        ),
        migrations.RemoveField(
            model_name='resource',
            name='preferred_in_report',
        ),
        migrations.RunSQL(
            sql='SET CONSTRAINTS ALL IMMEDIATE',
            reverse_sql='SET CONSTRAINTS ALL DEFERRED',
        ),
        migrations.AddField(
            model_name='city',
            name='subdivision_code',
            field=models.CharField(
                blank=True,
                max_length=10,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='country',
            name='country_calendar_code',
            field=models.CharField(
                blank=True,
                help_text=(
                    'Country calendar code as per https://holidays.readthedocs.io/en/latest/#available-countries'
                ),
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='contract',
            name='base_in',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='contracts',
                to='core.city',
            ),
        ),
        migrations.RunPython(forward_contract_base, backward_contract_base),
        migrations.RemoveField(
            model_name='contract',
            name='country_calendar_code',
        ),
        migrations.CreateModel(
            name='DayEntry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('day', models.DateField(help_text='Day')),
                ('last_modified', models.DateTimeField(auto_now=True)),
                ('closed', models.BooleanField(default=False, help_text='Submitted')),
                ('comment', models.TextField(blank=True, help_text='Notes', null=True)),
                (
                    'bank',
                    models.DecimalField(
                        decimal_places=2,
                        default=0.0,
                        help_text='Hours bank, positive deposits, negative withdrawals',
                        max_digits=4,
                    ),
                ),
                (
                    'due_hours',
                    models.DecimalField(decimal_places=2, default=0.0, help_text='Due hours for the day', max_digits=4),
                ),
                (
                    'travel_hours',
                    models.DecimalField(decimal_places=2, default=0.0, help_text='Travel hours', max_digits=4),
                ),
                (
                    'day_hours',
                    models.DecimalField(decimal_places=2, default=0.0, help_text='Day shift hours', max_digits=4),
                ),
                (
                    'night_hours',
                    models.DecimalField(decimal_places=2, default=0.0, help_text='Night shift hours', max_digits=4),
                ),
                (
                    'on_call_hours',
                    models.DecimalField(decimal_places=2, default=0.0, help_text='On call hours', max_digits=4),
                ),
                (
                    'is_holiday',
                    models.BooleanField(
                        default=False, help_text="Is Holiday for resource according to contract's calendar"
                    ),
                ),
                ('asked_holiday', models.BooleanField(default=False, help_text='Holiday requested by resource')),
                (
                    'leave_hours',
                    models.DecimalField(decimal_places=2, default=0.0, help_text='Leave hours', max_digits=4),
                ),
                (
                    'special_leave_hours',
                    models.DecimalField(decimal_places=2, default=0.0, help_text='Special leave hours', max_digits=4),
                ),
                ('protocol_number', models.CharField(blank=True, help_text='Sick certificate number', null=True)),
                ('is_sick', models.BooleanField(default=False, help_text='Resource called in sick')),
                (
                    'rest_hours',
                    models.DecimalField(decimal_places=2, default=0.0, help_text='Rest hours', max_digits=4),
                ),
                (
                    'overtime_hours',
                    models.DecimalField(
                        decimal_places=2, default=0.0, help_text='Overtime hours in the day', max_digits=4
                    ),
                ),
                ('meal_voucher', models.PositiveIntegerField(default=0, help_text='Meal voucher for the day')),
            ],
            options={
                'verbose_name_plural': 'Day entries',
            },
            bases=(krm3.utils.models.CleanValidatorsMixin, models.Model),
        ),
        migrations.CreateModel(
            name='TaskEntry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('day_shift_hours', models.DecimalField(decimal_places=2, max_digits=4)),
                ('night_shift_hours', models.DecimalField(decimal_places=2, default=0.0, max_digits=4)),
                ('on_call_hours', models.DecimalField(decimal_places=2, default=0.0, max_digits=4)),
                ('travel_hours', models.DecimalField(decimal_places=2, default=0.0, max_digits=4)),
                ('comment', models.TextField(blank=True, null=True)),
                ('metadata', models.JSONField(blank=True, default=dict, null=True)),
            ],
            options={
                'verbose_name_plural': 'Task entries',
                'permissions': [
                    ('view_any_timesheet', "Can view(only) everybody's timesheets"),
                    ('manage_any_timesheet', "Can view, and manage everybody's timesheets"),
                ],
            },
            bases=(krm3.utils.models.CleanValidatorsMixin, models.Model),
        ),
        migrations.RemoveField(
            model_name='resource',
            name='active',
        ),
        migrations.AlterField(
            model_name='resource',
            name='preferred_language',
            field=models.CharField(
                choices=[('en-uk', 'English'), ('it', 'Italiano'), ('fr', 'Français'), ('pl', 'Polski')],
                default='en-uk',
            ),
        ),
        migrations.RemoveField(
            model_name='task',
            name='basket_title',
        ),
        migrations.AddField(
            model_name='contract',
            name='overtime',
            field=models.BooleanField(default=True, help_text='Is overtime tracked'),
        ),
        migrations.AddField(
            model_name='po',
            name='period',
            field=django.contrib.postgres.fields.ranges.DateRangeField(
                default=(datetime.date(1970, 1, 1), datetime.date(2000, 1, 1)),
                help_text='N.B.: End date is the day after the actual end date',
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='project',
            name='period',
            field=django.contrib.postgres.fields.ranges.DateRangeField(
                default=(datetime.date(1970, 1, 1), datetime.date(2000, 1, 1)),
                help_text='N.B.: End date is the day after the actual end date',
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='task',
            name='basket',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='core.basket'
            ),
        ),
        migrations.AddField(
            model_name='task',
            name='period',
            field=django.contrib.postgres.fields.ranges.DateRangeField(
                default=(datetime.date(1970, 1, 1), datetime.date(2000, 1, 1)),
                help_text='N.B.: End date is the day after the actual end date',
            ),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='contract',
            name='period',
            field=django.contrib.postgres.fields.ranges.DateRangeField(
                help_text='N.B.: End date is the day after the actual end date'
            ),
        ),
        migrations.AlterField(
            model_name='contract',
            name='resource',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='core.resource'),
        ),
        migrations.AlterField(
            model_name='po',
            name='project',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='core.project'),
        ),
        migrations.AddField(
            model_name='dayentry',
            name='contract',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='core.contract'),
        ),
        migrations.AddField(
            model_name='dayentry',
            name='resource',
            field=models.ForeignKey(
                help_text='Resource', on_delete=django.db.models.deletion.PROTECT, to='core.resource'
            ),
        ),
        migrations.AddField(
            model_name='dayentry',
            name='special_leave_reason',
            field=models.ForeignKey(
                blank=True,
                help_text='Special leave reason',
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                to='core.specialleavereason',
            ),
        ),
        migrations.AddField(
            model_name='dayentry',
            name='timesheet',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='core.timesheetsubmission'
            ),
        ),
        migrations.AddField(
            model_name='taskentry',
            name='day_entry',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.dayentry'),
        ),
        migrations.AddField(
            model_name='taskentry',
            name='task',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT, related_name='task_entries', to='core.task'
            ),
        ),
        migrations.AddConstraint(
            model_name='dayentry',
            constraint=models.CheckConstraint(
                condition=models.Q(('special_leave_hours__range', (0, 24))), name='special_leave_hours_range'
            ),
        ),
        migrations.AddConstraint(
            model_name='dayentry',
            constraint=models.CheckConstraint(
                condition=models.Q(('leave_hours__range', (0, 24))), name='leave_hours_range'
            ),
        ),
        migrations.AddConstraint(
            model_name='dayentry',
            constraint=models.CheckConstraint(condition=models.Q(('bank__range', (-8, 8))), name='bank_range'),
        ),
        migrations.AddConstraint(
            model_name='dayentry',
            constraint=models.CheckConstraint(
                condition=models.Q(('rest_hours__range', (0, 24))), name='rest_hours_range'
            ),
        ),
        migrations.AddConstraint(
            model_name='taskentry',
            constraint=models.UniqueConstraint(fields=('day_entry', 'task'), name='unique_day_entry_task'),
        ),
        migrations.AddConstraint(
            model_name='taskentry',
            constraint=models.CheckConstraint(
                condition=models.Q(('day_shift_hours__range', (0, 16))), name='day_shift_hours_range'
            ),
        ),
        migrations.AddConstraint(
            model_name='taskentry',
            constraint=models.CheckConstraint(
                condition=models.Q(('night_shift_hours__range', (0, 8))), name='night_shift_hours_range'
            ),
        ),
        migrations.AddConstraint(
            model_name='taskentry',
            constraint=models.CheckConstraint(
                condition=models.Q(('on_call_hours__range', (0, 24))), name='on_call_hours_range'
            ),
        ),
        migrations.AddConstraint(
            model_name='taskentry',
            constraint=models.CheckConstraint(
                condition=models.Q(('travel_hours__range', (0, 24))), name='travel_hours_range'
            ),
        ),
        migrations.RunSQL(
            sql=migrations.RunSQL.noop,
            reverse_sql='SET CONSTRAINTS ALL IMMEDIATE',
        ),
        migrations.RunSQL(
            sql=MIGRATE_PERIODS_SQL,
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RunSQL(
            sql=CREATE_DAY_ENTRIES_SQL,
            reverse_sql=REVERSE_DAY_ENTRIES_SQL,
        ),
        migrations.RunSQL(
            sql=CREATE_TASK_ENTRIES_SQL,
            reverse_sql=REVERSE_TASK_ENTRIES_SQL,
        ),
        migrations.RunPython(
            code=recalculate_day_entries,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name='po',
            name='start_date',
            field=models.DateField(null=True),
        ),
        migrations.AlterField(
            model_name='project',
            name='start_date',
            field=models.DateField(null=True),
        ),
        migrations.AlterField(
            model_name='task',
            name='start_date',
            field=models.DateField(null=True),
        ),
        migrations.RunSQL(
            sql=migrations.RunSQL.noop,
            reverse_sql=RESTORE_LEGACY_PERIOD_DATES_SQL,
        ),
        migrations.RemoveField(
            model_name='po',
            name='end_date',
        ),
        migrations.RemoveField(
            model_name='po',
            name='start_date',
        ),
        migrations.RemoveField(
            model_name='project',
            name='end_date',
        ),
        migrations.RemoveField(
            model_name='project',
            name='start_date',
        ),
        migrations.RemoveField(
            model_name='task',
            name='end_date',
        ),
        migrations.RemoveField(
            model_name='task',
            name='start_date',
        ),
        migrations.DeleteModel(
            name='TimeEntry',
        ),
    ]
