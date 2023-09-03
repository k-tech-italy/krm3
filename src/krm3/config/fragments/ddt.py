# Debug toolbar
import logging as _logging

from django_regex.utils import RegexList as _RegexList

from krm3.config.environ import env as _env

if ddt_key := _env('DDT_KEY'):
    logger = _logging.getLogger(__name__)
    try:
        ignored = _RegexList(('/api/.*',))

        def show_ddt(request):
            """Runtime check for showing debug toolbar."""
            if not _env('DEBUG'):
                return False
            # use https://bewisse.com/modheader/ to set custom header
            # key must be `DDT-KEY` (no HTTP_ prefix, no underscores)
            if request.user.is_authenticated:
                if request.path in ignored:
                    return False
            return request.META.get('HTTP_DDT_KEY') == ddt_key

        DEBUG_TOOLBAR_CONFIG = {
            'SHOW_TOOLBAR_CALLBACK': show_ddt,
            'JQUERY_URL': '',
        }
        DEBUG_TOOLBAR_PANELS = _env('DDT_PANELS')

        # Testing for debug_toolbar presence
        import debug_toolbar  # noqa: F401

        DDT_MIDDLEWARES = ['debug_toolbar.middleware.DebugToolbarMiddleware']
        DDT_APPS = ['debug_toolbar']
        # CSP_REPORT_ONLY = True
    except ImportError:
        logger.info('Skipping debug toolbar')
