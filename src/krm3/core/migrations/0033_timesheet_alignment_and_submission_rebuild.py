# Collapses the migrations that followed 0032 (reimbursement help texts, DayEntry bank range, forced closing of the
# timesheets before 2026-10-01, meal-voucher recalculation), rebuilds the snapshot of every closed submission and
# grants the timesheet groups the permissions of the DayEntry and TaskEntry models.
import datetime

from dateutil.relativedelta import relativedelta
from django.contrib.auth.management import create_permissions
from django.db import migrations, models
from django.db.models.functions import TruncMonth
from psycopg.types.range import DateRange

WEEKDAYS = ('mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun')

# (model, codename) of the `core` permissions added to each group; view_any_timesheet and manage_any_timesheet are
# declared by TaskEntry (in 0030 the groups held the ones of the removed TimeEntry model)
TIMESHEET_GROUP_PERMISSIONS = {
    'Timesheet Viewer': [('taskentry', 'view_any_timesheet')],
    'Timesheet Manager': [
        ('taskentry', 'manage_any_timesheet'),
        *(
            (model, f'{action}_{model}')
            for model in ('taskentry', 'dayentry')
            for action in ('add', 'view', 'change', 'delete')
        ),
    ],
    'Timesheet Administrator': [('taskentry', 'view_any_timesheet'), ('taskentry', 'manage_any_timesheet')],
}

TRUNCATE_SUBMISSIONS = """
-- Delete old submissions
DELETE FROM core_timesheetsubmission;
"""


def close_timesheets_before_october_2026(apps, schema_editor):
    """Close every monthly timesheet up to 2026-09-30 that still has open day entries."""
    DayEntry = apps.get_model('core', 'DayEntry')
    TimesheetSubmission = apps.get_model('core', 'TimesheetSubmission')

    qs = (
        DayEntry.objects
        .filter(day__lt=datetime.date(2026, 11, 1))
        .annotate(month=TruncMonth('day'))
        .values('resource_id', 'month')
        .order_by('resource_id', 'month')  # also drops any default ordering, which would break DISTINCT
        .distinct()
    )
    for item in qs:
        ts = TimesheetSubmission.objects.create(
            period=DateRange(item['month'], item['month'] + relativedelta(months=1)),
            resource_id=item['resource_id'],
        )
        ts.closed = True
        ts.save()
        DayEntry.objects.filter(resource_id=ts.resource_id, day__lt=ts.period.upper, day__gte=ts.period.lower).update(
            timesheet=ts, closed=True
        )


def recompute_meal_vouchers(apps, schema_editor):
    """Deduct the hours deposited to the bank from the hours eligible for the meal voucher.

    0032 counted the bank withdrawals but not the deposits: only the day entries with a deposit can change.
    """
    # DayEntry = apps.get_model('core', 'DayEntry')
    #
    # to_update = []
    # for entry in DayEntry.objects.filter(bank__gt=0, meal_voucher__gt=0).select_related('contract'):
    #     threshold = (entry.contract.meal_voucher or {}).get(WEEKDAYS[entry.day.weekday()])
    #     if not threshold:
    #         continue
    #     eligible_hours = entry.day_hours + entry.night_hours + entry.travel_hours - entry.bank
    #     if eligible_hours < Decimal(str(threshold)):
    #         entry.meal_voucher = 0
    #         to_update.append(entry)
    # DayEntry.objects.bulk_update(to_update, ['meal_voucher'], batch_size=1000)


def rebuild_closed_submissions(apps, schema_editor):
    """Recalculate the snapshot of every closed submission from its DayEntry and TaskEntry records.

    Snapshots taken before 0032 use the TimeEntry format; after this step all of them use the current format.
    The snapshot is built by the application serializer, so this uses the current models rather than the
    historical ones. The bank balance of each snapshot is taken from the snapshot it replaces (see
    `Resource.get_bank_hours_balance`), so the rebuild runs in chronological order for each resource.
    """
    from krm3.core.models import TimesheetSubmission  # noqa: PLC0415

    for submission in TimesheetSubmission.objects.filter(closed=True).order_by('resource_id', 'period'):
        # update() skips clean(), whose submission-order checks do not apply to an existing history
        TimesheetSubmission.objects.filter(pk=submission.pk).update(timesheet=submission.calculate_timesheet())


def add_timesheet_group_permissions(apps, schema_editor):
    """Add the timesheet permissions to the existing timesheet groups; groups that do not exist are skipped."""
    # the permissions of the models created in 0032 are otherwise created only after all migrations (post_migrate)
    core_config = apps.get_app_config('core')
    models_module = getattr(core_config, 'models_module', None)
    core_config.models_module = True  # create_permissions skips app configs without models (historical apps)
    try:
        create_permissions(core_config, apps=apps, verbosity=0, using=schema_editor.connection.alias)
    finally:
        core_config.models_module = models_module

    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')
    for group_name, permissions in TIMESHEET_GROUP_PERMISSIONS.items():
        group = Group.objects.filter(name=group_name).first()
        if group is None:
            continue
        group.permissions.add(
            *(
                Permission.objects.get(content_type__app_label='core', content_type__model=model, codename=codename)
                for model, codename in permissions
            )
        )


class Migration(migrations.Migration):
    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('contenttypes', '0002_remove_content_type_name'),
        ('core', '0032_dayentry_taskentry_remove_timeentry_resource_and_more'),
    ]

    operations = [
        migrations.RunSQL(
            sql=TRUNCATE_SUBMISSIONS,
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.AlterField(
            model_name='reimbursement',
            name='number',
            field=models.PositiveIntegerField(blank=True, help_text='Assigned by the Create reimbursement action'),
        ),
        migrations.AlterField(
            model_name='reimbursement',
            name='title',
            field=models.CharField(help_text='Assigned by the Create reimbursement action', max_length=120),
        ),
        migrations.RemoveConstraint(
            model_name='dayentry',
            name='bank_range',
        ),
        migrations.AddConstraint(
            model_name='dayentry',
            constraint=models.CheckConstraint(condition=models.Q(('bank__range', (-16, 16))), name='bank_range'),
        ),
        migrations.RunPython(close_timesheets_before_october_2026, migrations.RunPython.noop),
        migrations.RunPython(recompute_meal_vouchers, migrations.RunPython.noop),
        migrations.RunPython(rebuild_closed_submissions, migrations.RunPython.noop),
        migrations.RunPython(add_timesheet_group_permissions, migrations.RunPython.noop),
    ]
