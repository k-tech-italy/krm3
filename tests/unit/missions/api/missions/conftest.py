import pytest


@pytest.fixture(autouse=True)
def missions_enabled(settings):
    """The missions API is gated by TRASFERTE_ENABLED (off by default)."""
    settings.FLAGS = {**settings.FLAGS, 'TRASFERTE_ENABLED': [('boolean', True)]}
