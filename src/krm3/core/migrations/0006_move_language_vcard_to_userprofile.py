import django.db.models.deletion
from django.apps.registry import Apps
from django.conf import settings
from django.db import migrations, models
from django.db.backends.base.schema import BaseDatabaseSchemaEditor


def forwards(apps: Apps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    """Copy preferred_language and vcard_text from each Resource to its user's profile.

    A Resource without a user has no profile to receive the values unless it is linked to one directly.
    """
    Resource = apps.get_model('core', 'Resource')  # noqa: N806
    UserProfile = apps.get_model('core', 'UserProfile')  # noqa: N806

    for resource in Resource.objects.select_related('user', 'profile'):
        if resource.user_id:
            profile, _ = UserProfile.objects.get_or_create(user_id=resource.user_id)
        elif resource.profile_id:
            profile = resource.profile
        else:
            continue
        profile.preferred_language = resource.preferred_language
        profile.vcard_text = resource.vcard_text
        profile.save(update_fields=['preferred_language', 'vcard_text'])


def backwards(apps: Apps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    Resource = apps.get_model('core', 'Resource')  # noqa: N806
    UserProfile = apps.get_model('core', 'UserProfile')  # noqa: N806

    for resource in Resource.objects.select_related('profile'):
        if resource.user_id:
            profile = UserProfile.objects.filter(user_id=resource.user_id).first()
        else:
            profile = resource.profile
        if profile is None:
            continue
        resource.preferred_language = profile.preferred_language
        resource.vcard_text = profile.vcard_text
        resource.save(update_fields=['preferred_language', 'vcard_text'])


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0005_rename_trasferte_flag'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='preferred_language',
            field=models.CharField(
                choices=[('en-uk', 'English'), ('it', 'Italiano'), ('fr', 'Français'), ('pl', 'Polski')],
                default='en-uk',
            ),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='vcard_text',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.RunPython(forwards, backwards),
        migrations.RemoveField(
            model_name='resource',
            name='preferred_language',
        ),
        migrations.RemoveField(
            model_name='resource',
            name='vcard_text',
        ),
        migrations.CreateModel(
            name='SavedFilter',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                (
                    'page',
                    models.CharField(
                        help_text='The page or table the filter applies to, e.g. "missions"', max_length=100
                    ),
                ),
                ('name', models.CharField(max_length=100)),
                (
                    'values',
                    models.JSONField(
                        blank=True, default=dict, help_text='Filter field name -> value or list of values'
                    ),
                ),
                (
                    'summary',
                    models.TextField(
                        blank=True,
                        default='',
                        help_text='The filter as people read it, e.g. "Resource: Jane Roe; From: 2025-01-01"',
                    ),
                ),
                (
                    'url',
                    models.CharField(
                        blank=True,
                        default='',
                        help_text='Frontend address that opens the page with this filter',
                        max_length=2000,
                    ),
                ),
                (
                    'is_default',
                    models.BooleanField(
                        default=False,
                        help_text='Applied when the page is loaded without filters; at most one per user and page',
                    ),
                ),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                (
                    'user',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='saved_filters',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                'ordering': ['page', 'name'],
                'constraints': [
                    models.UniqueConstraint(fields=('user', 'page', 'name'), name='unique_saved_filter_name_per_page'),
                    models.UniqueConstraint(
                        condition=models.Q(('is_default', True)),
                        fields=('user', 'page'),
                        name='one_default_saved_filter_per_page',
                    ),
                ],
            },
        ),
    ]
