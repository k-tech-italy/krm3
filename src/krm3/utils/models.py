from django.core.exceptions import ValidationError


class CleanValidatorsMixin:
    """Provide custom validators.

    It runs all cls._verify_** methods defined in the class during the clean method execution.
    """

    def clean(self) -> None:
        """Run parent validators and custom validators."""
        super().clean()
        self.custom_clean()

    def custom_clean(self) -> None:
        """Run custom validators"""
        errors = []
        for validator_name in sorted([x for x in self.__class__.__dict__ if x.startswith('_verify_')]):
            try:
                getattr(self, validator_name)()
            except ValidationError as e:
                errors.append(f'{validator_name}: {e}')

        if errors:
            raise ValidationError(errors)
