from django.db.models import Max
from rest_framework import serializers

from krm3.core.models import DocumentType, Expense, ExpenseCategory, Mission, PaymentCategory
from krm3.utils.serializers import ModelDefaultSerializerMetaclass


class MissionSerializer(metaclass=ModelDefaultSerializerMetaclass):
    class Meta:
        model = Mission
        fields = '__all__'


class MissionPaymentCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentCategory
        fields = ['id', 'title', '__str__', 'active', 'parent']


class MissionDocumentTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentType
        fields = ['id', 'title', 'active']


class MissionExpenseCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseCategory
        fields = ['id', 'title', '__str__', 'active', 'parent']


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


class MissionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Mission
        fields = (
            'title',
            'number',
            'from_date',
            'to_date',
            'year',
            'default_currency',
            'project',
            'city',
            'resource',
        )

    def create(self, validated_data):
        number = validated_data.get(
            'number', None
        )  # TODO from city ID to country default_currencies

        if number is None:
            last_number = Mission.objects.aggregate(Max('number'))['number__max']
            new_number = 1 if last_number is None else last_number + 1
            validated_data['number'] = new_number

        return super().create(validated_data)
