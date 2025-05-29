import random

from django.forms import ModelForm, TextInput, CharField

from krm3.core.models.projects import Task


def _pick_random_color(*args, **kwargs):
    return random.choice([
        'ED9B9B',
        '9E6B6B',
        'DECECE',
        '9A85A8',
        '769DC6',
        '315F90',
        '318F90',
        '2ADCDF',
        'B2ECA2',
        'D1E2AB'
    ])


class TaskForm(ModelForm):
    color = CharField(
        label='Choose a color',
        widget=TextInput(attrs={'type': 'color', 'value': '#333333'}),
        initial=_pick_random_color # Set your default color hex code here
    )

    def clean_color(self):
        if self.cleaned_data['color'] == '#000000':
            self.cleaned_data['color'] = None

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
