import typing

from django.conf import settings
from django.http import HttpRequest, HttpResponse

from krm3.utils.environments import environment_info

GetResponse = typing.Callable[[HttpRequest], HttpResponse]

API_PATH_PREFIX = '/api/'


class EnvironmentHeadersMiddleware:
    """Expose the deployment environment on API responses (Refs: taiga#715).

    Every ``/api/`` response carries ``X-environment``; non-production
    environments also carry ``X-env-color`` so the FE can render its banner.
    Templates get the same information from the ``admin_header`` context
    processor instead.
    """

    def __init__(self, get_response: GetResponse) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)

        if request.path.startswith(API_PATH_PREFIX):
            info = environment_info(settings.SENTRY_ENVIRONMENT)
            response['X-environment'] = info['environment']
            if info['show_banner']:
                response['X-env-color'] = info['color']

        return response
