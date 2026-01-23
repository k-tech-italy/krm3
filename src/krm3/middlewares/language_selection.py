from django.conf import settings
from django.utils import translation
from django.http import HttpResponse


class UserLanguageMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request) -> HttpResponse:
        # Check if language is already set in session (priority 1)
        session_language = request.COOKIES.get(settings.LANGUAGE_COOKIE_NAME)

        if not session_language and request.user.is_authenticated:
            # Priority 2: Use profile language if no session override exists
            if hasattr(request.user, 'resource'):
                if user_preferred_language := getattr(request.user.resource, 'preferred_language', None):
                    translation.activate(user_preferred_language)
                    request.LANGUAGE_CODE = user_preferred_language

        # Priority 3: Browser headers
        return self.get_response(request)
