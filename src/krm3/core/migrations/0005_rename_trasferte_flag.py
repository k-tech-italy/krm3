from django.apps.registry import Apps
from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor

OLD_NAME = 'TRASFERTE_ENABLED'
NEW_NAME = 'MISSIONS_ENABLED'


def _rename(apps: Apps, old: str, new: str) -> None:
    FlagState = apps.get_model('flags', 'FlagState')  # noqa: N806
    FlagState.objects.filter(name=old).update(name=new)


def forwards(apps: Apps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    """Keep the conditions stored in the database for the renamed missions flag."""
    _rename(apps, OLD_NAME, NEW_NAME)


def backwards(apps: Apps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    _rename(apps, NEW_NAME, OLD_NAME)


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0004_delete_task_entry_chat_threads'),
        ('flags', '0014_flagstate_unique_constraint'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
