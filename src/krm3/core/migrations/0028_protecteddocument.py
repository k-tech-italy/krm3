# Generated manually for proxy model

from django.db import migrations


class Migration(migrations.Migration):
    """Create ProtectedDocument proxy model.

    This proxy model extends django_simple_dms.Document with a file_url property
    for serving files through protected media views.
    """

    dependencies = [
        ('core', '0027_use_private_storage'),
        ('django_simple_dms', '0003_configurable_storage'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProtectedDocument',
            fields=[],
            options={
                'proxy': True,
                'verbose_name': 'Document',
                'verbose_name_plural': 'Documents',
                'indexes': [],
                'constraints': [],
            },
            bases=('django_simple_dms.document',),
        ),
    ]
