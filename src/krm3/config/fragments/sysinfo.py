from django.conf import settings

SYSINFO = {
    'extra': {
        'GIT': 'krm3.utils.sysinfo.get_commit_info',
        'TICKETING_ENABLED': settings.TICKETING_ENABLED,
    },
    'masker': 'krm3.utils.sysinfo.masker',
}
