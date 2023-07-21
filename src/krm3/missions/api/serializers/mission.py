from rest_framework import serializers

from krm3.missions.models import Mission
from krm3.utils.serializers import ModelDefaultSerializerMetaclass


class MissionSerializer(metaclass=ModelDefaultSerializerMetaclass):
    class Meta:
        model = Mission
        fields = '__all__'


class MissionNestedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Mission
        fields = '__all__'
        depth = 2
