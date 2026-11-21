from django.apps.registry import Apps
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
    ]
