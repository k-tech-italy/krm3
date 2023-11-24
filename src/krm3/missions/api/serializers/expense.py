from cryptography.fernet import InvalidToken
from django.conf import settings
from rest_framework import serializers

from krm3.missions.models import DocumentType, Expense, ExpenseCategory, PaymentCategory
from krm3.utils.serializers import ModelDefaultSerializerMetaclass


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
            'amount_base',
            'amount_reimbursement',
            'detail',
            'category',
            'document_type',
            'payment_type',
            'reimbursement',
            'image',
            'created_ts',
            'modified_ts'
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


# class ExportExpenseSerializer(serializers.ModelSerializer):
#
#     def __init__(self, instance=None, *args, **kwargs):
#         exclude = kwargs.pop('exclude', None)
#         super().__init__(instance, *args, **kwargs)
#
#         if exclude is not None:
#             for field_name in exclude:
#                 self.fields.pop(field_name)
#
#     class Meta:
#         model = Expense
#         # fields = []
#         fields = '__all__'
#         # fields = ['day', 'amount_currency', 'amount_base', 'amount_reimbursement', 'detail', 'category',
#         #           'payment_type', 'reimbursement', 'created_ts', 'modified_ts']
#         depth = 2

class ExpenseNestedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expense
        fields = '__all__'
        depth = 2
