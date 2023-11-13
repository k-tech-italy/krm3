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
    name = factory.Sequence(lambda n: f'Country {n + 1}')
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
    year = factory.LazyAttribute(lambda obj: obj.from_date.year)

    class Meta:
        model = 'missions.Mission'


class ExpenseCategoryFactory(factory.django.DjangoModelFactory):
    title = factory.Sequence(lambda n: n + 1)

    class Meta:
        model = 'missions.ExpenseCategory'


class PaymentCategoryFactory(factory.django.DjangoModelFactory):
    title = factory.Sequence(lambda n: n + 1)

    class Meta:
        model = 'missions.PaymentCategory'


class DocumentTypeFactory(factory.django.DjangoModelFactory):
    title = factory.Sequence(lambda n: f'DT {n + 1}')

    class Meta:
        model = 'missions.DocumentType'


class ExpenseFactory(factory.django.DjangoModelFactory):
    mission = factory.SubFactory(MissionFactory)
    amount_currency = FuzzyDecimal(0.5, 170)
    day = factory.LazyAttribute(
        lambda obj: obj.mission.from_date
    )
    currency = factory.SubFactory(CurrencyFactory)
    category = factory.SubFactory(ExpenseCategoryFactory)
    payment_type = factory.SubFactory(PaymentCategoryFactory)
    document_type = factory.SubFactory(DocumentTypeFactory)

    class Meta:
        model = 'missions.Expense'


class RateFactory(factory.django.DjangoModelFactory):
    day = factory.Faker(
        'date_between_dates',
        date_start=date(2020, 1, 1),
        date_end=date(2022, 12, 31),
    )

    class Meta:
        model = 'currencies.Rate'


class ReimbursementFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = 'missions.Reimbursement'
