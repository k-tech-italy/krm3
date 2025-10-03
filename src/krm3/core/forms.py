import datetime

from django.core.exceptions import ValidationError
from django.forms import ModelForm

from krm3.core.models import Contract
from krm3.utils.dates import DATE_INFINITE


class ContractForm(ModelForm):
    def clean(self) -> dict:
        ret = super().clean()
        if (
            self.instance
            and (new_period := self.cleaned_data.get('period'))
            and (self.cleaned_data.get('resource'))
        ):
            old_period = [self.instance.period.lower, self.instance.period.upper or DATE_INFINITE]
            new_period = [new_period.lower, new_period.upper or DATE_INFINITE]

            # check if interval becomes smaller
            if new_period[1] < old_period[1] or new_period[0] > old_period[0]:
                for task in self.instance.get_tasks():
                    task_period = [task.start_date, task.end_date or DATE_INFINITE]
                    if (new_period[0] > old_period[0] and new_period[0] > task_period[0]) or (
                        new_period[1] < old_period[1] and new_period[1] - datetime.timedelta(days=1) < task_period[1]
                    ):
                        raise ValidationError('Shrinking contract period would leave orphan tasks', code='orphan-tasks')

        return ret

    class Meta:
        model = Contract
        fields = '__all__'  # noqa: DJ007
