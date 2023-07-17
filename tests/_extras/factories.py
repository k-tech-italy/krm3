from datetime import date

import factory
from dateutil.relativedelta import relativedelta
from factory.fuzzy import FuzzyDecimal

from krm3.core.models import User


class UserFactory(factory.django.DjangoModelFactory):
    username = factory.Sequence(lambda n: 'User %02d' % n)
    email = factory.Sequence(lambda n: 'u%02d@wfp.org' % n)

    class Meta:
        model = User


class CountryFactory(factory.django.DjangoModelFactory):
    name = factory.Faker('country')

    # florida = factory.LazyAttribute(lambda x: faker.florida())

    class Meta:
        model = 'core.Country'


class CityFactory(factory.django.DjangoModelFactory):
    name = factory.Faker('city')
    country = factory.SubFactory(CountryFactory)

    class Meta:
        model = 'core.City'


class CurrencyFactory(factory.django.DjangoModelFactory):
    iso3 = factory.Sequence(lambda n: str(n + 1))
    title = factory.Sequence(lambda n: str(n + 1))
    symbol = factory.Sequence(lambda n: str(n + 1))
    base = 100

    class Meta:
        model = 'currencies.Currency'


class ResourceFactory(factory.django.DjangoModelFactory):
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')

    class Meta:
        model = 'core.Resource'


class ClientFactory(factory.django.DjangoModelFactory):
    name = factory.Faker('company')

    class Meta:
        model = 'core.Client'


class ProjectFactory(factory.django.DjangoModelFactory):
    name = factory.Faker('job')
    client = factory.SubFactory(ClientFactory)

    class Meta:
        model = 'core.Project'


class MissionFactory(factory.django.DjangoModelFactory):
    number = factory.Sequence(lambda n: n + 1)
    from_date = factory.Faker('date_between_dates',
                              date_start=date.fromisoformat('2020-01-01'),
                              date_end=date.fromisoformat('2020-10-01'))
    to_date = factory.LazyAttribute(
        lambda obj: obj.from_date + relativedelta(days=5)
    )

    project = factory.SubFactory(ProjectFactory)
    # country = factory.SubFactory(CountryFactory)
    city = factory.SubFactory(CityFactory)
    resource = factory.SubFactory(ResourceFactory)
    default_currency = factory.SubFactory(CurrencyFactory)

    class Meta:
        model = 'missions.Mission'


class ExpenseFactory(factory.django.DjangoModelFactory):
    mission = factory.SubFactory(MissionFactory)
    amount_currency = FuzzyDecimal(0.5, 170)
    day = factory.LazyAttribute(
        lambda obj: obj.mission.from_date
    )
    currency = factory.SubFactory(CurrencyFactory)

    class Meta:
        model = 'missions.Expense'
