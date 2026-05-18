from django.core.management import call_command
from django.db import migrations


def forward(apps: object, schema_editor: object) -> None:
    """Create necessary DayEntry objects."""
    call_command('migrate_day_entries')


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0032_timeentry_contract_alter_resource_preferred_language_and_more'),
    ]

    operations = [
        migrations.RunPython(forward, migrations.RunPython.noop),
    ]
