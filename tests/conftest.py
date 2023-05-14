import sys
from pathlib import Path

import pytest


def pytest_configure(config):
    here = Path(__file__).parent
    # root = here.parent.parent
    sys.path.insert(0, str(here / '_extras'))


@pytest.fixture()
def country(db):
    from factories import CountryFactory
    return CountryFactory()


@pytest.fixture()
def city(db):
    from factories import CityFactory
    return CityFactory()


@pytest.fixture()
def resource(db):
    from factories import ResourceFactory
    return ResourceFactory()


@pytest.fixture()
def project(db):
    from factories import ProjectFactory
    return ProjectFactory()


@pytest.fixture()
def client(db):
    from factories import ClientFactory
    return ClientFactory()


@pytest.fixture()
def mission(db):
    from factories import MissionFactory
    return MissionFactory()


# @pytest.fixture()
# def mission(db):
#     return MissionFactory()
