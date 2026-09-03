import pytest
from django.core.exceptions import ValidationError

from krm3.utils.models import CleanValidatorsMixin


class BaseCleanModel:
    def clean(self) -> None:
        pass


class MultipleValidatorModel(CleanValidatorsMixin, BaseCleanModel):
    def _verify_first(self) -> None:
        raise ValidationError('First error')

    def _verify_second(self) -> None:
        raise ValidationError(['Second error', 'Third error'])


def test_clean_validators_collect_messages_without_validator_names():
    with pytest.raises(ValidationError) as exc_info:
        MultipleValidatorModel().clean()

    assert exc_info.value.messages == ['First error', 'Second error', 'Third error']
