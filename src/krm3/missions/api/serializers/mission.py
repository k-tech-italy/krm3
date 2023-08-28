from rest_framework import serializers

from krm3.missions.models import DocumentType, Expense, ExpenseCategory, Mission, PaymentCategory
from krm3.utils.serializers import ModelDefaultSerializerMetaclass


class MissionSerializer(metaclass=ModelDefaultSerializerMetaclass):
    class Meta:
        model = Mission
        fields = '__all__'


class MissionPaymentCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentCategory
        fields = ['id', '__str__', 'active']


class MissionDocumentTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentType
        fields = ['id', 'title', 'active']


class MissionExpenseCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseCategory
        fields = ['id', '__str__', 'active']


class MissionExpenseSerializer(serializers.ModelSerializer):
    category = MissionExpenseCategorySerializer()
    document_type = MissionDocumentTypeSerializer()
    payment_type = MissionPaymentCategorySerializer()

    class Meta:
        model = Expense
        exclude = ['mission']


class MissionNestedSerializer(serializers.ModelSerializer):
    expenses = MissionExpenseSerializer(many=True, read_only=True)

    class Meta:
        model = Mission
        fields = '__all__'
        depth = 2
