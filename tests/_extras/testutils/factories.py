from datetime import date, timedelta

import factory
from dateutil.relativedelta import relativedelta
from django.contrib.auth.models import Group
from factory import Faker, Sequence, SubFactory
from factory.base import FactoryMetaClass
from factory.django import DjangoModelFactory
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


class AutoRegisterModelFactory(DjangoModelFactory, metaclass=AutoRegisterFactoryMetaClass):
    pass


def get_factory_for_model(_model):
    class Meta:
        model = _model

    if _model in factories_registry:
        return factories_registry[_model]
    return type(f'{_model._meta.model_name}AutoFactory', (AutoRegisterModelFactory,), {'Meta': Meta})


class UserFactory(DjangoModelFactory):
    username = Sequence(lambda n: 'User %02d' % n)
    email = Sequence(lambda n: 'u%02d@example.com' % n)
    password = factory.PostGenerationMethodCall('set_password', 'password')

    @classmethod
    def _after_postgeneration(cls, instance, create, results=None):
        super()._after_postgeneration(instance, create, results)
        instance._password = 'password'

    class Meta:
        model = User
        django_get_or_create = ('username',)


class SuperUserFactory(UserFactory):
    username = Sequence(lambda n: 'superuser%03d@example.com' % n)
    email = Sequence(lambda n: 'superuser%03d@example.com' % n)
    is_superuser = True
    is_staff = True
    is_active = True


class GroupFactory(DjangoModelFactory):
    name = Sequence(lambda n: 'Group %02d' % n)

    class Meta:
        model = Group
        django_get_or_create = ('name',)


class CountryFactory(DjangoModelFactory):
    name = Faker('country')

    class Meta:
        model = 'core.Country'
        django_get_or_create = ('name',)


class CityFactory(DjangoModelFactory):
    name = Sequence(lambda n: f'Country {n + 1}')
    country = SubFactory(CountryFactory)

    class Meta:
        model = 'core.City'


class CurrencyFactory(DjangoModelFactory):
    iso3 = Sequence(lambda n: str(n + 1))
    title = Sequence(lambda n: str(n + 1))
    symbol = Sequence(lambda n: str(n + 1))
    base = 100

    class Meta:
        model = 'currencies.Currency'
        django_get_or_create = ('iso3',)


class ResourceFactory(DjangoModelFactory):
    first_name = Faker('first_name')
    last_name = Faker('last_name')
    user = SubFactory(UserFactory)
    preferred_in_report = True

    class Meta:
        model = 'core.Resource'
        django_get_or_create = ('first_name', 'last_name')


class ContractFactory(DjangoModelFactory):
    resource = SubFactory(ResourceFactory)
    period = (date(2020, 1, 1), None)
    country_calendar_code = settings.HOLIDAYS_CALENDAR

    class Meta:
        model = 'core.Contract'


class ExtraHolidayFactory(DjangoModelFactory):
    period = Sequence(lambda n: generate_month_period(date(2020, 1, 1), n))
    country_codes = [settings.HOLIDAYS_CALENDAR]
    reason = 'King coronation'

    class Meta:
        model = 'core.ExtraHoliday'


class ClientFactory(DjangoModelFactory):
    name = Faker('company')

    class Meta:
        model = 'core.Client'
        django_get_or_create = ('name',)


class ProjectFactory(DjangoModelFactory):
    name = Faker('job')
    client = SubFactory(ClientFactory)
    start_date = date(2020, 1, 1)

    class Meta:
        model = 'core.Project'
        django_get_or_create = ('name',)


class MissionFactory(DjangoModelFactory):
    number = Sequence(lambda n: n + 1)
    from_date = Faker(
        'date_between_dates', date_start=date.fromisoformat('2020-01-01'), date_end=date.fromisoformat('2020-10-01')
    )
    to_date = factory.LazyAttribute(lambda obj: obj.from_date + relativedelta(days=5))

    project = SubFactory(ProjectFactory)
    city = SubFactory(CityFactory)
    resource = SubFactory(ResourceFactory)
    default_currency = factory.Iterator(Currency.objects.all())
    year = factory.LazyAttribute(lambda obj: obj.from_date.year)
    status = 'SUBMITTED'

    class Meta:
        model = 'core.Mission'


class ExpenseCategoryFactory(DjangoModelFactory):
    title = Sequence(lambda n: n + 1)

    class Meta:
        model = 'core.ExpenseCategory'


class PaymentCategoryFactory(DjangoModelFactory):
    title = Sequence(lambda n: n + 1)

    class Meta:
        model = 'core.PaymentCategory'


class DocumentTypeFactory(DjangoModelFactory):
    title = Sequence(lambda n: f'DT {n + 1}')

    class Meta:
        model = 'core.DocumentType'


class ExpenseFactory(DjangoModelFactory):
    mission = SubFactory(MissionFactory)
    amount_currency = FuzzyDecimal(0.5, 170)
    day = factory.LazyAttribute(lambda obj: obj.mission.from_date)
    currency = SubFactory(CurrencyFactory)
    category = SubFactory(ExpenseCategoryFactory)
    payment_type = SubFactory(PaymentCategoryFactory)
    document_type = SubFactory(DocumentTypeFactory)
    amount_base = factory.LazyAttribute(lambda o: o.amount_currency)
    amount_reimbursement = factory.LazyAttribute(lambda o: o.amount_currency if o.payment_type.personal_expense else 0)

    class Meta:
        model = 'core.Expense'


class RateFactory(DjangoModelFactory):
    day = Faker(
        'date_between_dates',
        date_start=date(2020, 1, 1),
        date_end=date(2022, 12, 31),
    )

    class Meta:
        model = 'currencies.Rate'


class ReimbursementFactory(DjangoModelFactory):
    title = Sequence(lambda n: f'Tit {n + 1}')
    year = 2024
    month = 'April'
    resource = SubFactory(ResourceFactory)

    class Meta:
        model = 'core.Reimbursement'


class POFactory(DjangoModelFactory):
    ref = Sequence(lambda n: f'Ext_{n + 1:04}')
    project = SubFactory(ProjectFactory)
    start_date = factory.fuzzy.FuzzyDate(date(2022, 1, 1), date.today() - timedelta(days=60))

    class Meta:
        model = 'core.PO'


class BasketFactory(DjangoModelFactory):
    title = Faker('sentence', nb_words=3)
    initial_capacity = FuzzyDecimal(100, 5000)
    po = SubFactory(POFactory)

    class Meta:
        model = 'core.Basket'


class TaskFactory(DjangoModelFactory):
    title = Faker('sentence', nb_words=3)
    work_price = Faker('random_int', min=100, max=1000)
    project = SubFactory(ProjectFactory)
    resource = SubFactory(ResourceFactory)
    start_date = factory.LazyAttribute(lambda obj: obj.project.start_date)

    class Meta:
        model = 'core.Task'
        django_get_or_create = ('title', 'project', 'resource')


def generate_month_period(start_date, offset):
    start_dt = start_date + relativedelta(months=offset)
    end_dt = start_dt + relativedelta(months=1)
    return start_dt, end_dt


class TimesheetSubmissionFactory(DjangoModelFactory):
    period = Sequence(lambda n: generate_month_period(date(2020, 1, 1), n))
    resource = SubFactory(ResourceFactory)

    class Meta:
        model = 'core.TimesheetSubmission'


class TimeEntryFactory(DjangoModelFactory):
    date = Faker('date_between_dates', date_start=date(2020, 1, 1), date_end=date(2023, 12, 31))
    day_shift_hours = Faker('random_int', min=0, max=8)
    resource = SubFactory(ResourceFactory)

    class Meta:
        model = 'core.TimeEntry'


class InvoiceFactory(DjangoModelFactory):
    number = Sequence(lambda n: f'Inv_{n + 1:04}')

    class Meta:
        model = 'core.Invoice'


class InvoiceEntryFactory(DjangoModelFactory):
    amount = Faker('random_int', min=10, max=100)
    basket = SubFactory(BasketFactory)
    invoice = SubFactory(InvoiceFactory)

    class Meta:
        model = 'core.InvoiceEntry'


class SpecialLeaveReasonFactory(DjangoModelFactory):
    title = Faker('sentence', nb_words=4)

    class Meta:
        model = 'core.SpecialLeaveReason'
        django_get_or_create = ('title',)


# Django Simple DMS Factories
class DocumentFactory(DjangoModelFactory):
    class Meta:
        model = 'django_simple_dms.Document'

    document = factory.django.FileField(filename='test_document.txt', data=b'test content')
    admin = factory.SubFactory(UserFactory)


class DocumentTagFactory(DjangoModelFactory):
    class Meta:
        model = 'django_simple_dms.DocumentTag'

    title = factory.Sequence(lambda n: f'tag{n}')


class DocumentGrantFactory(DjangoModelFactory):
    class Meta:
        model = 'django_simple_dms.DocumentGrant'

    user = factory.SubFactory(UserFactory)
    document = factory.SubFactory(DocumentFactory)
    granted_permissions = ['R']
