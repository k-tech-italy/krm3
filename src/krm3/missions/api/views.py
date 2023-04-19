from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from krm3.missions.models import Mission


class MissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Mission
        fields = '__all__'


class MissionAPIViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = MissionSerializer
    queryset = Mission.objects.all()
