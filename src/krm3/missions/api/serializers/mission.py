from rest_framework import serializers

from krm3.missions.models import Mission


class MissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Mission
        fields = '__all__'


class ExportMissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Mission
        fields = '__all__'
        depth = 3
