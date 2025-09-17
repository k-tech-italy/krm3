from ..environ import env

TICKETING_ENABLED = False

if (
    (token := env('TICKETING_TOKEN'))
    and (project_id := env('TICKETING_PROJECT_ID'))
    and (issues := env('TICKETING_ISSUES'))
):
    TICKETING_ENABLED = True
    ISSUES = {
        'BACKEND': 'issues.backends.taiga.Backend',
        'TYPES': dict([x.split(',') for x in issues.split(';')]),
        'OPTIONS': {
            'API_URL': env('TICKETING_URL', default='https://api.taiga.io'),
            'API_TOKEN': token,
            'PROJECT_ID': project_id,
            'TAGS': ['online'],
        },
    }
