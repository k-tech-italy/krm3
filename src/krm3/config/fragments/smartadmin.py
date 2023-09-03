# Add this to settings.INSTALLED_APPS
SMART_ADMIN_APPS = [
    'smart_admin.apps.SmartTemplateConfig',
    'smart_admin.apps.SmartLogsConfig',
    'smart_admin.apps.SmartAuthConfig',
    'smart_admin.apps.SmartConfig',
]

SMART_ADMIN_SECTIONS = {
    'Core': [
        'core.City',
        'core.Client',
        'core.Country',
        'core.Project',
        'core.Resource',
    ],
    'Missions': [
        'missions',
    ],
    '_hidden_': ['sites'],
    'Security': [
        'auth',
        'admin.LogEntry',
        'social_django',
        'core.UserProfile',
        'core.User',
        'token_blacklist'
    ],
    'Configuration': [
        'constance',
        'flags',
        'currencies'
    ]
}
