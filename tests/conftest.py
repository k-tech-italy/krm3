import pytest

from .factories import CityFactory, ClientFactory, CountryFactory, MissionFactory, ProjectFactory, ResourceFactory

# @pytest.fixture()
# def country_italy(db):
#     return Country.objects.create(name='Italy')
#
#
# @pytest.fixture()
# def city_rome(country_italy):
#     City.objects.create(name='Rome', country=country_italy)


@pytest.fixture()
def country(db):
    return CountryFactory()


@pytest.fixture()
def city(db):
    return CityFactory()


@pytest.fixture()
def resource(db):
    return ResourceFactory()


@pytest.fixture()
def project(db):
    return ProjectFactory()


@pytest.fixture()
def client(db):
    return ClientFactory()


@pytest.fixture()
def mission(db):
    return MissionFactory()


# @pytest.fixture()
# def mission(db):
#     return MissionFactory()
