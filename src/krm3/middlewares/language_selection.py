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
        # Check if language is already set in cookies
        language_cookie_name = settings.LANGUAGE_COOKIE_NAME
        response = self.get_response(request)

        response_language = response.cookies.get(language_cookie_name, '')
        request_language = request.COOKIES.get(language_cookie_name, '')

        # Only update language when strictly necessary
        if (request_language and response_language) and (request_language != response_language.value):
            return self._set_response_language(
                response=response,
                language=response_language.value,
                language_cookie_name=language_cookie_name
            )

        # We don't have a language in the cookie, check the resource
        if not request_language and request.user.is_authenticated:
            if (
                hasattr(request.user, 'resource')
                and (user_preferred_language := getattr(request.user.resource, 'preferred_language', None))
            ):
                return self._set_response_language(
                    response=response,
                    language=user_preferred_language,
                    language_cookie_name=language_cookie_name
                )

        # Fall back to the original response
        return response

    def _set_response_language(self, response: HttpResponse, language_cookie_name: str, language: str) -> HttpResponse:
        """Set language of the response."""
        translation.activate(language)
        response.LANGUAGE_CODE = language
        response.set_cookie(language_cookie_name, language)
        return response
