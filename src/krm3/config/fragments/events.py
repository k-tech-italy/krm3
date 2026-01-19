from krm3.config.environ import env

__all__ = ['EVENTS']

EVENTS = {
    'BACKEND': env('EVENT_DISPATCHER_BACKEND'),
    'OPTIONS': env('EVENT_DISPATCHER_OPTIONS'),
}
