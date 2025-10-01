
from datetime import date, timedelta

import factory
from dateutil.relativedelta import relativedelta
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from factory import PostGenerationMethodCall
from factory.base import FactoryMetaClass
from factory.fuzzy import FuzzyDecimal

from krm3.config import settings
from krm3.core.models import User
from krm3.currencies.models import Currency

factories_registry = {}


class AutoRegisterFactoryMetaClass(FactoryMetaClass):
    def __new__(cls, class_name, bases, attrs):
        new_class = super().__new__(cls, class_name, bases, attrs)
        factories_registry[new_class._meta.model] = new_class
        return new_class


class AutoRegisterModelFactory(factory.django.DjangoModelFactory, metaclass=AutoRegisterFactoryMetaClass):
    pass


def get_factory_for_model(_model):
    class Meta:
        model = _model

    if _model in factories_registry:
        return factories_registry[_model]
    return type(f'{_model._meta.model_name}AutoFactory', (AutoRegisterModelFactory,), {'Meta': Meta})


class UserFactory(AutoRegisterModelFactory):
    username = factory.Sequence(lambda d: 'username-%s' % d)
    email = factory.Faker('email')
    first_name = factory.Faker('name')
    last_name = factory.Faker('last_name')
    password = PostGenerationMethodCall('set_password', 'password')

    class Meta:
        model = get_user_model()
        django_get_or_create = ('username',)


class SuperUserFactory(UserFactory):
    username = factory.Sequence(lambda n: 'superuser%03d@example.com' % n)
    email = factory.Sequence(lambda n: 'superuser%03d@example.com' % n)
    is_superuser = True
    is_staff = True
    is_active = True


class GroupFactory(factory.django.DjangoModelFactory):
    name = factory.Sequence(lambda n: 'Group %02d' % n)

    class Meta:
        model = Group
        django_get_or_create = ('name',)


class UserFactory(factory.django.DjangoModelFactory):
    username = factory.Sequence(lambda n: 'User %02d' % n)
    email = factory.Sequence(lambda n: 'u%02d@example.com' % n)
    password = factory.PostGenerationMethodCall('set_password', 'password')

    @classmethod
    def _after_postgeneration(cls, instance, create, results=None):
        super()._after_postgeneration(instance, create, results)
        instance._password = 'password'

    class Meta:
        model = User
        django_get_or_create = ('username',)


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

class ContractFactory(factory.django.DjangoModelFactory):
    resource = factory.SubFactory(ResourceFactory)
    period = factory.Sequence(
        lambda n: generate_month_period(date(2020, 1, 1), n)
    )
    country_calendar_code = settings.HOLIDAYS_CALENDAR

    class Meta:
        model = 'core.Contract'

class ExtraHolidayFactory(factory.django.DjangoModelFactory):
    period = factory.Sequence(
        lambda n: generate_month_period(date(2020, 1, 1), n)
    )
    country_codes = [settings.HOLIDAYS_CALENDAR]
    reason = "King coronation"

    class Meta:
        model = 'core.ExtraHoliday'


class ClientFactory(factory.django.DjangoModelFactory):
    name = factory.Faker('company')

    class Meta:
        model = 'core.Client'
        django_get_or_create = ('name',)


class ProjectFactory(factory.django.DjangoModelFactory):
    name = factory.Faker('job')
    client = factory.SubFactory(ClientFactory)
    start_date = date(2020, 1, 1)

    class Meta:
        model = 'core.Project'
        django_get_or_create = ('name',)


class MissionFactory(factory.django.DjangoModelFactory):
    number = factory.Sequence(lambda n: n + 1)
    from_date = factory.Faker(
        'date_between_dates', date_start=date.fromisoformat('2020-01-01'), date_end=date.fromisoformat('2020-10-01')
    )
    to_date = factory.LazyAttribute(lambda obj: obj.from_date + relativedelta(days=5))

    project = factory.SubFactory(ProjectFactory)
    city = factory.SubFactory(CityFactory)
    resource = factory.SubFactory(ResourceFactory)
    default_currency = factory.Iterator(Currency.objects.all())
    year = factory.LazyAttribute(lambda obj: obj.from_date.year)
    status = 'SUBMITTED'

    class Meta:
        model = 'core.Mission'
        django_get_or_create = ('year', 'number')


class ExpenseCategoryFactory(factory.django.DjangoModelFactory):
    title = factory.Sequence(lambda n: n + 1)

    class Meta:
        model = 'core.ExpenseCategory'


class PaymentCategoryFactory(factory.django.DjangoModelFactory):
    title = factory.Sequence(lambda n: n + 1)

    class Meta:
        model = 'core.PaymentCategory'


class DocumentTypeFactory(factory.django.DjangoModelFactory):
    title = factory.Sequence(lambda n: f'DT {n + 1}')

    class Meta:
        model = 'core.DocumentType'


class ExpenseFactory(factory.django.DjangoModelFactory):
    mission = factory.SubFactory(MissionFactory)
    amount_currency = FuzzyDecimal(0.5, 170)
    day = factory.LazyAttribute(lambda obj: obj.mission.from_date)
    currency = factory.SubFactory(CurrencyFactory)
    category = factory.SubFactory(ExpenseCategoryFactory)
    payment_type = factory.SubFactory(PaymentCategoryFactory)
    document_type = factory.SubFactory(DocumentTypeFactory)
    amount_base = factory.LazyAttribute(lambda o: o.amount_currency)
    amount_reimbursement = factory.LazyAttribute(lambda o: o.amount_currency if o.payment_type.personal_expense else 0)

    class Meta:
        model = 'core.Expense'


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
    month = 'April'
    resource = factory.SubFactory(ResourceFactory)

    class Meta:
        model = 'core.Reimbursement'


class POFactory(factory.django.DjangoModelFactory):
    ref = factory.Sequence(lambda n: f'Ext_{n + 1:04}')
    project = factory.SubFactory(ProjectFactory)
    start_date = factory.fuzzy.FuzzyDate(date(2022, 1, 1), date.today() - timedelta(days=60))

    class Meta:
        model = 'core.PO'


class BasketFactory(factory.django.DjangoModelFactory):
    title = factory.Faker('sentence', nb_words=3)
    initial_capacity = FuzzyDecimal(100, 5000)
    po = factory.SubFactory(POFactory)

    class Meta:
        model = 'core.Basket'


class TaskFactory(factory.django.DjangoModelFactory):
    title = factory.Faker('sentence', nb_words=3)
    work_price = factory.Faker('random_int', min=100, max=1000)
    project = factory.SubFactory(ProjectFactory)
    resource = factory.SubFactory(ResourceFactory)
    start_date = factory.LazyAttribute(lambda obj: obj.project.start_date)

    class Meta:
        model = 'core.Task'
        django_get_or_create = ('title', 'project', 'resource')


def generate_month_period(start_date, offset):
    start_dt = start_date + relativedelta(months=offset)
    end_dt = start_dt + relativedelta(months=1)
    return start_dt, end_dt


class TimesheetSubmissionFactory(factory.django.DjangoModelFactory):
    period = factory.Sequence(
        lambda n: generate_month_period(date(2020, 1, 1), n)
    )
    resource = factory.SubFactory(ResourceFactory)

    class Meta:
        model = 'core.TimesheetSubmission'


class TimeEntryFactory(factory.django.DjangoModelFactory):
    date = factory.Faker('date_between_dates', date_start=date(2020, 1, 1), date_end=date(2023, 12, 31))
    day_shift_hours = factory.Faker('random_int', min=0, max=8)
    resource = factory.SubFactory(ResourceFactory)
    # NOTE: comments are defined as optional, but they can be mandatory
    # in some situations - see test suite.
    # Providing a comment is always safe, NOT providing it is not!
    comment = factory.Faker('sentence', nb_words=10)

    class Meta:
        model = 'core.TimeEntry'


class InvoiceFactory(factory.django.DjangoModelFactory):
    number = factory.Sequence(lambda n: f'Inv_{n + 1:04}')

    class Meta:
        model = 'core.Invoice'


class InvoiceEntryFactory(factory.django.DjangoModelFactory):
    amount = factory.Faker('random_int', min=10, max=100)
    basket = factory.SubFactory(BasketFactory)
    invoice = factory.SubFactory(InvoiceFactory)

    class Meta:
        model = 'core.InvoiceEntry'


class SpecialLeaveReasonFactory(factory.django.DjangoModelFactory):
    title = factory.Faker('sentence', nb_words=4)

    class Meta:
        model = 'core.SpecialLeaveReason'
