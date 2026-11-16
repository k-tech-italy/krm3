from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0001_initial'),
        ('django_simple_dms', '0003_configurable_storage'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProtectedDocument',
            fields=[
            ],
            options={
                'verbose_name': 'Document',
                'verbose_name_plural': 'Documents',
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('django_simple_dms.document',),
        ),
    ]
