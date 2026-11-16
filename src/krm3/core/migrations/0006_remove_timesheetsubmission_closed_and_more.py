from django.db import migrations, models


def forwards(apps, schema_editor):
    TimesheetSubmission = apps.get_model('core', 'TimesheetSubmission')
    TimesheetSubmission.objects.filter(closed=True).update(status='closed')
    TimesheetSubmission.objects.filter(closed=False).update(status='draft')


def backwards(apps, schema_editor):
    TimesheetSubmission = apps.get_model('core', 'TimesheetSubmission')
    TimesheetSubmission.objects.filter(status='closed').update(closed=True)
    TimesheetSubmission.objects.exclude(status='closed').update(closed=False)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_rename_trasferte_flag'),
    ]

    operations = [
        migrations.AddField(
            model_name='timesheetsubmission',
            name='status',
            field=models.CharField(choices=[('draft', 'Draft'), ('pending', 'Pending'), ('rejected', 'Rejected'), ('closed', 'Closed')], db_index=True, default='draft', max_length=16),
        ),
        migrations.RunPython(forwards, backwards),
        migrations.RemoveField(
            model_name='timesheetsubmission',
            name='closed',
        ),
        migrations.AddField(
            model_name='timesheetsubmission',
            name='rejection_message',
            field=models.TextField(blank=True, default=''),
        ),
    ]
