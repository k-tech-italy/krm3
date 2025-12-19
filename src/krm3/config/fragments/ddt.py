"""Debug toolbar settings fragments.

Add DDT_MIDDLEWARES to settings.MIDDLEWARES
Add DDT_APPS to settings.INSTALLED_APPS
"""

import logging as _logging
import os
import sys

from django_regex.utils import RegexList as _RegexList
from flags.state import flag_enabled

from ..environ import env as _env

TESTING = 'test' in sys.argv or 'PYTEST_VERSION' in os.environ

DDT_APPS = []
DDT_MIDDLEWARES = []

if not TESTING:
    logger = _logging.getLogger(__name__)
    try:
        ignored = _RegexList(('/api/.*',))

        def show_ddt(request):
            """Runtime check for showing debug toolbar."""
            if not _env('DEBUG') or request.path in ignored:
                return False
            # use https://bewisse.com/modheader/ to set custom header
            # key must be `DDT-KEY` (no HTTP_ prefix, no underscores)`
            if flag_enabled('DDT_ENABLED', request=request):
                return True
            return False

        DEBUG_TOOLBAR_CONFIG = {
            'SHOW_TOOLBAR_CALLBACK': show_ddt,
            'JQUERY_URL': '',
        }
        DEBUG_TOOLBAR_PANELS = _env('DDT_PANELS')

        # Testing for debug_toolbar presence
        import debug_toolbar  # noqa: F401

        DDT_MIDDLEWARES = ['debug_toolbar.middleware.DebugToolbarMiddleware']
        DDT_APPS = ['debug_toolbar']
        INTERNAL_IPS = _env('INTERNAL_IPS')
        # CSP_REPORT_ONLY = True
    except ImportError:
        logger.info('Skipping debug toolbar')
