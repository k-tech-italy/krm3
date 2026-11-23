import copy
from typing import Any

from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.translation import gettext_lazy as _
from ktcalendars import KTDay
from rest_framework import serializers

from krm3.core.api.views import ResourceSerializer
from krm3.core.models import DocumentType, Expense, ExpenseCategory, Mission, PaymentCategory, Project
from krm3.utils.serializers import ModelDefaultSerializerMetaclass, PrivateMediaFileField


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
    image = PrivateMediaFileField(url_field='image_url', required=False, allow_null=True)
    currency_symbol = serializers.CharField(source='currency.symbol', read_only=True)

    class Meta:
        model = Expense
        exclude = ['mission']


class MissionTotalsSerializer(serializers.Serializer):
    refund = serializers.DecimalField(max_digits=12, decimal_places=2)
    anticipated = serializers.DecimalField(max_digits=12, decimal_places=2)
    total = serializers.DecimalField(max_digits=12, decimal_places=2)


class MissionNestedSerializer(serializers.ModelSerializer):
    expenses = MissionExpenseSerializer(many=True, read_only=True)
    resource = ResourceSerializer(many=False, read_only=True)
    totals = MissionTotalsSerializer(source='expense_totals', read_only=True)

    class Meta:
        model = Mission
        fields = '__all__'
        depth = 2


class MissionCreateSerializer(serializers.ModelSerializer):
    """Create/update a mission.

    `number` is read-only: missions are created in DRAFT and the number is
    assigned when they are submitted (see `Mission.submit`).
    Users without `core.manage_any_mission` can only use their own resource.
    The project must be one the resource is involved in today or later (see `Project.objects.involving`);
    this is checked on create and when the project or the resource change.
    """

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        # only mission managers can create or move missions for other resources
        request = self.context.get('request')
        resource = attrs.get('resource')
        if (
            resource is not None
            and request is not None
            and not request.user.has_perm('core.manage_any_mission')
            and resource.user_id != request.user.pk
        ):
            raise serializers.ValidationError({'resource': [_('You can only use your own resource')]})

        self._validate_project_involvement(attrs)

        # validate on a copy, so the model invariants surface as 400 instead of 500
        instance = copy.copy(self.instance) if self.instance else Mission()
        for attr, value in attrs.items():
            setattr(instance, attr, value)
        try:
            instance.clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages)
        return attrs

    def _validate_project_involvement(self, attrs: dict[str, Any]) -> None:
        if self.instance is not None and all(
            field not in attrs or attrs[field] == getattr(self.instance, field) for field in ('project', 'resource')
        ):
            return
        project = attrs.get('project', getattr(self.instance, 'project', None))
        resource = attrs.get('resource', getattr(self.instance, 'resource', None))
        if (
            project is not None
            and resource is not None
            and not Project.objects.involving(resource, KTDay().date).filter(pk=project.pk).exists()
        ):
            raise serializers.ValidationError(
                {'project': [_('The resource has no current or future task in this project')]}
            )

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
        read_only_fields = ('number',)
