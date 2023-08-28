from rest_framework import serializers

from krm3.missions.api.serializers.expense import ExpenseSerializer
from krm3.missions.models import Mission
from krm3.utils.serializers import ModelDefaultSerializerMetaclass


class MissionSerializer(metaclass=ModelDefaultSerializerMetaclass):
    class Meta:
        model = Mission
        fields = '__all__'


class MissionNestedSerializer(serializers.ModelSerializer):
    expenses = ExpenseSerializer(many=True, read_only=True)

    class Meta:
        model = Mission
        fields = ['number', 'title', 'from_date', 'to_date', 'year', 'default_currency', 'project', 'city', 'resource',
                  'expenses']
        # fields = '__all__'
        depth = 2
