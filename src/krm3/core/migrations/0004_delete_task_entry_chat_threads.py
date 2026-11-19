from django.apps.registry import Apps
from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor


def delete_task_entry_threads(apps: Apps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    """Task entries can no longer have a chat thread: drop the existing ones with their messages."""
    ContentType = apps.get_model('contenttypes', 'ContentType')  # noqa: N806
    ChatThread = apps.get_model('core', 'ChatThread')  # noqa: N806
    ct = ContentType.objects.filter(app_label='core', model='taskentry').first()
    if ct is not None:
        ChatThread.objects.filter(content_type=ct).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('core', '0003_chat'),
    ]

    operations = [
        migrations.RunPython(delete_task_entry_threads, migrations.RunPython.noop),
    ]
