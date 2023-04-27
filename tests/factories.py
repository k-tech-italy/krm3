import factory
from dateutil.relativedelta import relativedelta


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
    from_date = factory.Faker('date_between')
    to_date = factory.LazyAttribute(
        lambda obj: obj.from_date + relativedelta(days=5)
    )

    project = factory.SubFactory(ProjectFactory)
    # country = factory.SubFactory(CountryFactory)
    city = factory.SubFactory(CityFactory)
    resource = factory.SubFactory(ResourceFactory)

    class Meta:
        model = 'missions.Mission'
