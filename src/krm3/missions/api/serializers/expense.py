from cryptography.fernet import InvalidToken
from django.conf import settings
from rest_framework import serializers

from krm3.missions.models import Expense


def token_validator(value):
    try:
        settings.FERNET_KEY.decrypt(f'gAAAAA{value}').decode()
    except InvalidToken:
        raise serializers.ValidationError('OTP is invalid')


class ExpenseImageUploadSerializer(serializers.ModelSerializer):
    otp = serializers.CharField(max_length=200, validators=[token_validator])

    class Meta:
        model = Expense
        fields = ['otp', 'image']


class ExpenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expense
        fields = '__all__'


class ExpenseRetrieveSerializer(serializers.ModelSerializer):
    otp = serializers.SerializerMethodField()

    @staticmethod
    def get_otp(obj: Expense):  # noqa: D102
        return obj.get_otp()

    class Meta:
        model = Expense
        fields = ['otp']
