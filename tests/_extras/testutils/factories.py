import factory.fuzzy
from django.contrib.auth import get_user_model
from factory import PostGenerationMethodCall
from factory.base import FactoryMetaClass

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
