import datetime

import django.contrib.postgres.fields.ranges
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0031_contract_sunday_as_holiday'),
    ]

    operations = [
        migrations.AddField(
            model_name='contract',
            name='overtime',
            field=models.BooleanField(default=True, help_text='Is overtime tracked'),
        ),
        migrations.RemoveField(
            model_name='resource',
            name='active',
        ),
        migrations.AlterField(
            model_name='timeentry',
            name='timesheet',
            field=models.ForeignKey(blank=True,
                                    null=True, on_delete=django.db.models.deletion.SET_NULL,
                                    to='core.timesheetsubmission', ),
            preserve_default=False,
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
        migrations.RemoveConstraint(
            model_name='timeentry',
            name='sick_hours_range',
        ),
        migrations.RemoveConstraint(
            model_name='timeentry',
            name='holiday_hours_range',
        ),
        migrations.RemoveConstraint(
            model_name='timeentry',
            name='leave_hours_range',
        ),
        migrations.RemoveConstraint(
            model_name='timeentry',
            name='special_leave_hours_range',
        ),
        migrations.RemoveConstraint(
            model_name='timeentry',
            name='rest_hours_range',
        ),
        migrations.RemoveConstraint(
            model_name='timeentry',
            name='bank_to_range',
        ),
        migrations.RemoveConstraint(
            model_name='timeentry',
            name='bank_from_range',
        ),
        migrations.AlterField(
            model_name='resource',
            name='preferred_language',
            field=models.CharField(
                choices=[('en-uk', 'English'), ('it', 'Italiano'), ('fr', 'Français'), ('pl', 'Polski')],
                default='en-uk',
            ),
        ),
        migrations.CreateModel(
            name='DayEntry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('day', models.DateField(help_text='Day')),
                ('last_modified', models.DateTimeField(auto_now=True)),
                ('closed', models.BooleanField(default=False, help_text='Submitted')),
                ('comment', models.TextField(blank=True, help_text='Notes', null=True)),
                ('contract', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='core.contract')),
                (
                    'timesheet',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to='core.timesheetsubmission',
                    ),
                ),
                (
                    'resource',
                    models.ForeignKey(
                        help_text='Resource', on_delete=django.db.models.deletion.PROTECT, to='core.resource'
                    ),
                ),
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
                (
                    'special_leave_reason',
                    models.ForeignKey(
                        blank=True,
                        help_text='Special leave reason',
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        to='core.specialleavereason',
                    ),
                ),
                ('protocol_number', models.CharField(blank=True, null=True, help_text='Sick certificate number')),
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
            constraint=models.CheckConstraint(
                condition=models.Q(('rest_hours__range', (0, 24))), name='rest_hours_range'
            ),
        ),
        migrations.AddConstraint(
            model_name='dayentry',
            constraint=models.CheckConstraint(condition=models.Q(('bank__range', (-8, 8))), name='bank_range'),
        ),
        migrations.AddField(
            model_name='timeentry',
            name='day_entry',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='core.dayentry'
            ),
        ),
        migrations.RenameModel(
            old_name='TimeEntry',
            new_name='TaskEntry',
        ),
        migrations.AlterField(
            model_name='taskentry',
            name='task',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                                    related_name='task_entries', to='core.task'),
        ),
        migrations.AddConstraint(
            model_name='taskentry',
            constraint=models.UniqueConstraint(fields=('day_entry', 'task'), name='unique_day_entry_task'),
        ),
        migrations.AddField(
            model_name='po',
            name='period',
            field=django.contrib.postgres.fields.ranges.DateRangeField(
                default=(datetime.date(1900, 1, 1), datetime.date(9999, 12, 31)),
                help_text='N.B.: End date is the day after the actual end date',
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='project',
            name='period',
            field=django.contrib.postgres.fields.ranges.DateRangeField(
                default=(datetime.date(1900, 1, 1), datetime.date(9999, 12, 31)),
                help_text='N.B.: End date is the day after the actual end date',
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='task',
            name='period',
            field=django.contrib.postgres.fields.ranges.DateRangeField(
                default=(datetime.date(1900, 1, 1), datetime.date(9999, 12, 31)),
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

    ]
