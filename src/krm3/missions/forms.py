from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models import Max
from django.forms import FileField, Form, ModelForm

from krm3.currencies.models import Currency
from krm3.missions.impexp.imp import MissionImporter
from krm3.missions.models import Expense, Mission


class MissionAdminForm(ModelForm):

    def clean(self):
        ret = super().clean()

        if not self.cleaned_data.get('default_currency'):
            self.cleaned_data['default_currency'] = Currency.objects.get(pk=settings.BASE_CURRENCY)

        if (from_date := self.cleaned_data.get('from_date')) and not self.cleaned_data['year']:
            self.cleaned_data['year'] = from_date.year

        if (from_date := self.cleaned_data.get('from_date')) and self.cleaned_data.get('number', None) is None:
            qs = Mission.objects.filter(from_date__year=self.cleaned_data['year'])
            if self.instance.id:
                qs = qs.exclude(pk=self.instance.id)
            number = qs.aggregate(Max('number'))['number__max'] or 0
            self.cleaned_data['number'] = number + 1
        else:
            if self.cleaned_data.get('number', None) is None:
                self.add_error('number', ValidationError('Number requires from_Date to be autocalculated',
                                                         code='invalid'))

        return ret

    class Meta:
        model = Mission
        fields = '__all__'


class ExpenseAdminForm(ModelForm):

    def clean(self):
        ret = super().clean()

        if not self.cleaned_data.get('currency') and (mission := self.cleaned_data['mission']):
            self.cleaned_data['currency'] = mission.default_currency

        return ret

    class Meta:
        model = Expense
        fields = '__all__'


class MissionsImportForm(Form):
    """Accepts .zip missions dump to import."""

    file = FileField(help_text='Load the missions zip file')

    def is_valid(self):
        ret = super().is_valid()
        if ret:
            MissionImporter(self.cleaned_data['file']).validate()
        return ret
