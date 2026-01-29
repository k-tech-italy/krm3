from .auth import *  # noqa: F401, F403
from .geo import *  # noqa: F401, F403
from .contacts import *  # noqa: F401, F403
from .contracts import *  # noqa: F401, F403
from .projects import *  # noqa: F401, F403
from .missions import *  # noqa: F401, F403
from .timesheets import *  # noqa: F401, F403
from .accounting import *  # noqa: F401, F403


def __getattr__(name: str): # noqa: ANN202
    """Lazy import for ProtectedDocument to avoid circular import with django-simple-dms."""
    if name == 'ProtectedDocument':
        from .documents import ProtectedDocument
        return ProtectedDocument
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
