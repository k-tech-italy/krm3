from cryptography.fernet import InvalidToken
from django.conf import settings
from drf_extra_fields.fields import HybridImageField
from rest_framework import serializers

from krm3.core.models import DocumentType, Expense, ExpenseCategory, PaymentCategory
from krm3.utils.serializers import ModelDefaultSerializerMetaclass


def token_validator(value):
    try:
        settings.FERNET_KEY.decrypt(f'gAAAAA{value}').decode()
    except InvalidToken:
        raise serializers.ValidationError('OTP is invalid')


class ExpenseCategorySerializer(metaclass=ModelDefaultSerializerMetaclass):

    class Meta:
        model = ExpenseCategory
        fields = ['id', '__str__', 'title', 'active', 'parent']


class PaymentCategorySerializer(metaclass=ModelDefaultSerializerMetaclass):
    class Meta:
        model = PaymentCategory
        fields = ['id', '__str__', 'title', 'active', 'parent']


class DocumentTypeSerializer(metaclass=ModelDefaultSerializerMetaclass):
    class Meta:
        model = DocumentType
        fields = ['id', '__str__', 'title', 'active', 'default']


class ExpenseSerializer(metaclass=ModelDefaultSerializerMetaclass):
    category = ExpenseCategorySerializer()
    document_type = DocumentTypeSerializer()
    payment_type = PaymentCategorySerializer()

    class Meta:
        model = Expense
        fields = '__all__'
        read_only_fields = ['amount_base']


class ExpenseCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = Expense
        fields = (
            'mission',
            'day',
            'amount_currency',
            'currency',
            'detail',
            'category',
            'document_type',
            'payment_type',
            'image'
        )


class ExpenseExportSerializer(serializers.ModelSerializer):

    class Meta:
        model = Expense
        fields = '__all__'
        read_only_fields = ['amount_base']


class ExpenseRetrieveSerializer(serializers.ModelSerializer):
    otp = serializers.SerializerMethodField()

    @staticmethod
    def get_otp(obj: Expense):  # noqa: D102
        return obj.get_otp()

    class Meta:
        model = Expense
        fields = ['otp']
