import importlib

import pytest

from krm3.config import environ
from krm3.config.fragments import bitcaster


@pytest.mark.parametrize('sync_users', (True, False))
def test_bitcaster_settings(monkeypatch, sync_users):
    values = {
        'KRM3_BITCASTER_BAE': 'https://token@bitcaster.example/api/o/acme/',
        'KRM3_BITCASTER_PROJECT_SLUG': 'krm3',
        'KRM3_BITCASTER_APPLICATION': 'web',
        'KRM3_BITCASTER_DISTRIBUTION_LIST': 'employees',
        'KRM3_BITCASTER_SYNC_USERS': str(sync_users),
    }
    for key, value in values.items():
        monkeypatch.setitem(environ.env.ENVIRON, key, value)

    reloaded = importlib.reload(bitcaster)

    assert {
        'BAE': values['KRM3_BITCASTER_BAE'],
        'PROJECT': values['KRM3_BITCASTER_PROJECT_SLUG'],
        'APPLICATION': values['KRM3_BITCASTER_APPLICATION'],
        'DISTRIBUTION_LIST': values['KRM3_BITCASTER_DISTRIBUTION_LIST'],
        'SYNC_USERS': sync_users,
    } == reloaded.BITCASTER
