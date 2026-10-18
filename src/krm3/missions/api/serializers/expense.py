import typing

from cryptography.fernet import InvalidToken
from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from krm3.core.models import DocumentType, Expense, ExpenseCategory, PaymentCategory
from krm3.utils.serializers import ModelDefaultSerializerMetaclass


def token_validator(value: str) -> None:
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
    def validate(self, attrs: dict[str, typing.Any]) -> dict[str, typing.Any]:
        # only expense managers can add (or move) expenses to missions of other resources
        request = self.context.get('request')
        mission = attrs.get('mission')
        if (
            mission is not None
            and request is not None
            and not request.user.has_perm('core.manage_any_expense')
            and mission.resource.user_id != request.user.pk
        ):
            raise serializers.ValidationError({'mission': [_('You can only add expenses to your own missions')]})

        instance = self.instance or Expense()
        for attr, value in attrs.items():
            setattr(instance, attr, value)
        try:
            instance.clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict)
        return attrs

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
            'image',
        )


class ExpenseExportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expense
        fields = '__all__'
        read_only_fields = ['amount_base']


class ExpenseRetrieveSerializer(serializers.ModelSerializer):
    otp = serializers.SerializerMethodField()

    @staticmethod
    def get_otp(obj: Expense) -> object:  # noqa: D102
        return obj.get_otp()

    class Meta:
        model = Expense
        fields = ['otp']
