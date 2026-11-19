import pytest


@pytest.fixture(autouse=True)
def missions_enabled(settings):
    """The missions API is gated by MISSIONS_ENABLED (off by default)."""
    settings.FLAGS = {**settings.FLAGS, 'MISSIONS_ENABLED': [('boolean', True)]}
