from django.db import migrations

def forward(apps, schema_editor) -> None:  # noqa: ANN001
    from krm3.core.models import TimesheetSubmission

    for obj in TimesheetSubmission.objects.all():
        obj.timesheet = None if obj.closed is False else obj.calculate_timesheet()
        obj.save()


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0020_alter_timesheetsubmission_timesheet'),
    ]

    operations = [
        migrations.RunPython(forward, migrations.RunPython.noop),
    ]
