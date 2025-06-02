from django import forms
from django_jsonform.widgets import JSONFormWidget
from django_pydantic_field.forms import SchemaField

from krm3.core.models import TimeEntry, SpecialLeaveReason
from krm3.core.pyd_models import Hours




class TimeEntryJSONFormWidget(JSONFormWidget):

    def __init__(self, schema, model_name='', file_handler='', validate_on_submit=False, attrs=None):
        super().__init__(schema, model_name, file_handler, validate_on_submit, attrs)
        self.schema['properties']['special_leave_reason_id'] = {
            'type': 'integer', 'default': None, 'title': 'Special Leave Reason Id',
            'choices': list(SpecialLeaveReason.objects.order_by('title').values_list('title', flat=True))
        }


class TimeEntryForm(forms.ModelForm):
    hours = SchemaField(Hours, widget=TimeEntryJSONFormWidget)

    def full_clean(self):
        super().full_clean()

    def clean_hours(self):
        print(self.hours)

    class Meta:
        model = TimeEntry
        fields = "__all__"
