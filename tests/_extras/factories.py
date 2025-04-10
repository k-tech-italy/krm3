from datetime import date

import factory
from dateutil.relativedelta import relativedelta
from factory.fuzzy import FuzzyDecimal

from krm3.core.models import User
from krm3.currencies import models


class UserFactory(factory.django.DjangoModelFactory):
    username = factory.Sequence(lambda n: 'User %02d' % n)
    email = factory.Sequence(lambda n: 'u%02d@example.com' % n)

    class Meta:
        model = User


class CountryFactory(factory.django.DjangoModelFactory):
    name = factory.Faker('country')

    class Meta:
        model = 'core.Country'
        django_get_or_create = ('name',)


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
        django_get_or_create = ('iso3',)


class ResourceFactory(factory.django.DjangoModelFactory):
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')

    class Meta:
        model = 'core.Resource'
        django_get_or_create = ('first_name', 'last_name')


class ClientFactory(factory.django.DjangoModelFactory):
    name = factory.Faker('company')

    class Meta:
        model = 'core.Client'
        django_get_or_create = ('name',)


class ProjectFactory(factory.django.DjangoModelFactory):
    name = factory.Faker('job')
    client = factory.SubFactory(ClientFactory)

    class Meta:
        model = 'core.Project'
        django_get_or_create = ('name', 'client')


class MissionFactory(factory.django.DjangoModelFactory):
    number = factory.Sequence(lambda n: n + 1)
    from_date = factory.Faker(
        'date_between_dates', date_start=date.fromisoformat('2020-01-01'), date_end=date.fromisoformat('2020-10-01')
    )
    to_date = factory.LazyAttribute(lambda obj: obj.from_date + relativedelta(days=5))

    project = factory.SubFactory(ProjectFactory)
    city = factory.SubFactory(CityFactory)
    resource = factory.SubFactory(ResourceFactory)
    default_currency = factory.Iterator(models.Currency.objects.all())
    year = factory.LazyAttribute(lambda obj: obj.from_date.year)
    status = 'SUBMITTED'

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
    day = factory.LazyAttribute(lambda obj: obj.mission.from_date)
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
    title = factory.Sequence(lambda n: f'Tit {n + 1}')
    year = 2024
    resource = factory.SubFactory(ResourceFactory)

    class Meta:
        model = 'missions.Reimbursement'


class POFactory(factory.django.DjangoModelFactory):
    ref = factory.Sequence(lambda n: f'Ext_{n + 1:04}')
    project = factory.SubFactory(ProjectFactory)

    class Meta:
        model = 'timesheet.PO'


class BasketFactory(factory.django.DjangoModelFactory):
    title = factory.Faker('sentence', nb_words=3)
    initial_capacity = FuzzyDecimal(100, 5000)
    po = factory.SubFactory(POFactory)

    class Meta:
        model = 'timesheet.Basket'


class TaskFactory(factory.django.DjangoModelFactory):
    title = factory.Faker('sentence', nb_words=3)
    work_price = factory.Faker('random_int', min=100, max=1000)
    project = factory.SubFactory(ProjectFactory)
    resource = factory.SubFactory(ResourceFactory)

    class Meta:
        model = 'timesheet.Task'


class TimeEntryFactory(factory.django.DjangoModelFactory):
    date = factory.Faker('date_between_dates', date_start=date(2020, 1, 1), date_end=date(2023, 12, 31))
    work_hours = factory.Faker('random_int', min=0, max=8)
    task = factory.SubFactory(TaskFactory)
    resource = factory.LazyAttribute(lambda entry: entry.task.resource)

    class Meta:
        model = 'timesheet.TimeEntry'


class InvoiceFactory(factory.django.DjangoModelFactory):
    number = factory.Sequence(lambda n: f'Inv_{n + 1:04}')

    class Meta:
        model = 'accounting.Invoice'


class InvoiceEntryFactory(factory.django.DjangoModelFactory):
    amount = factory.Faker('random_int', min=10, max=100)
    basket = factory.SubFactory(BasketFactory)
    invoice = factory.SubFactory(InvoiceFactory)

    class Meta:
        model = 'accounting.InvoiceEntry'
