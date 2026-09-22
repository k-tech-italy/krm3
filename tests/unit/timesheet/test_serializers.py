from django.core.exceptions import ValidationError
from rest_framework import serializers

from krm3.timesheet.api.serializers import _model_validation_error_detail


def test_model_validation_errors_are_joined_into_one_api_error():
    detail = _model_validation_error_detail(
        ValidationError(['First error', 'Second error', 'Third error'])
    )

    error = serializers.ValidationError(detail)

    assert error.detail == {
        'error': 'First error; Second error; Third error',
    }


def test_model_field_validation_errors_keep_their_structure():
    detail = _model_validation_error_detail(
        ValidationError({'field': ['First error', 'Second error']})
    )

    assert detail == {'field': ['First error', 'Second error']}
