from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0033_migrate_time_entries'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='taskentry',
            name='last_modified',
        ),
        migrations.AlterField(
            model_name='taskentry',
            name='day_entry',
            field=models.ForeignKey(on_delete=models.deletion.CASCADE, to='core.dayentry'),
        ),
        migrations.RemoveField(
            model_name='taskentry',
            name='bank_from',
        ),
        migrations.RemoveField(
            model_name='taskentry',
            name='bank_to',
        ),
        migrations.RemoveField(
            model_name='taskentry',
            name='holiday_hours',
        ),
        migrations.RemoveField(
            model_name='taskentry',
            name='leave_hours',
        ),
        migrations.RemoveField(
            model_name='taskentry',
            name='rest_hours',
        ),
        migrations.RemoveField(
            model_name='taskentry',
            name='sick_hours',
        ),
        migrations.RemoveField(
            model_name='taskentry',
            name='special_leave_hours',
        ),
        migrations.RemoveField(
            model_name='taskentry',
            name='special_leave_reason',
        ),
        migrations.RemoveField(
            model_name='taskentry',
            name='date',
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
        migrations.RemoveField(
            model_name='taskentry',
            name='resource',
        ),
        migrations.RemoveField(
            model_name='taskentry',
            name='timesheet',
        ),
        migrations.AlterField(
            model_name='taskentry',
            name='task',
            field=models.ForeignKey(on_delete=models.deletion.PROTECT, related_name='task_entries', to='core.task'),
        ),
        migrations.AlterModelOptions(
            name='dayentry',
            options={'verbose_name_plural': 'Day entries'},
        ),
        migrations.AlterModelOptions(
            name='taskentry',
            options={'permissions': [('view_any_timesheet', "Can view(only) everybody's timesheets"),
                                     ('manage_any_timesheet', "Can view, and manage everybody's timesheets")],
                     'verbose_name_plural': 'Task entries'},
        ),
        migrations.RemoveField(
            model_name='taskentry',
            name='protocol_number',
        ),
    ]
