from krm3.currencies.models import Currency, Rate
from krm3.utils.serializers import ModelDefaultSerializerMetaclass


class CurrencySerializer(metaclass=ModelDefaultSerializerMetaclass):
    class Meta:
        fields = '__all__'
        model = Currency


class RateSerializer(metaclass=ModelDefaultSerializerMetaclass):
    class Meta:
        fields = '__all__'
        model = Rate
