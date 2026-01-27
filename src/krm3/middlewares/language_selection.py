import typing

from django.conf import settings
from django.utils import translation
from django.http import HttpResponse
from django.http import HttpRequest

GetResponse = typing.Callable[[HttpRequest], HttpResponse]


class UserLanguageMiddleware:
    def __init__(self, get_response: GetResponse) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Check if language is already set in session (priority 1)
        language_cookie_name = settings.LANGUAGE_COOKIE_NAME
        if session_language_cookie := request.COOKIES.get(language_cookie_name):
            response = self.get_response(request)
            response.LANGUAGE_CODE = session_language_cookie
            response.set_cookie(language_cookie_name, session_language_cookie)
            return response

        if not session_language_cookie and request.user.is_authenticated:
            # Priority 2: Use profile language if no session override exists
            if hasattr(request.user, 'resource'):  #noqa: SIM102 - combining ifs would lose readability
                if user_preferred_language := getattr(request.user.resource, 'preferred_language', None):
                    translation.activate(user_preferred_language)

                    response = self.get_response(request)
                    response.LANGUAGE_CODE = user_preferred_language
                    response.set_cookie(language_cookie_name, user_preferred_language)
                    return response

        # Priority 3: Browser headers
        return self.get_response(request)
