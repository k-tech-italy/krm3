from rest_framework import serializers

from krm3.missions.models import Expense


class ExpenseImageUploadSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(required=False)

    class Meta:
        model = Expense
        fields = ['image']


class ExpenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expense
        fields = '__all__'
