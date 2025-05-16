from django.forms import ModelForm, TextInput

from krm3.core.models.projects import Task


class TaskForm(ModelForm):
    class Meta:
        model = Task
        fields = [
            'title',
            'basket_title',
            'project',
            'resource',
            'color',
            'start_date',
            'end_date',
            'work_price',
            'on_call_price',
            'travel_price',
            'overtime_price',
            'project',
            'resource',
        ]
        widgets = {
            'color': TextInput(attrs={'type': 'color'}),
        }
