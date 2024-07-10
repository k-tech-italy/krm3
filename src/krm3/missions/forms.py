import datetime

from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError

from krm3.currencies.models import Currency
from krm3.missions.facilities import ReimbursementFacility
from krm3.missions.impexp.imp import MissionImporter
from krm3.missions.models import Expense, Mission, Reimbursement


class MissionAdminForm(forms.ModelForm):

    def calculate_number(self) -> int:
        return Mission.calculate_number(self.instance and self.instance.id, self.cleaned_data['year'])

    def clean_number(self):
        number = self.cleaned_data['number']
        if number and number <= 0:
            raise ValidationError('Number must be > 0')

    def clean(self):
        """Clean data."""
        ret = super().clean()

        # set year from from_date
        if (from_date := self.cleaned_data.get('from_date')) and not self.cleaned_data['year']:
            self.cleaned_data['year'] = from_date.year

        # take settings.BASE_CURRENCY if no currency specified
        if not self.cleaned_data.get('default_currency'):
            self.cleaned_data['default_currency'] = Currency.objects.get(pk=settings.BASE_CURRENCY)

        # if SUBMITTED
        if self.cleaned_data.get('status') != Mission.MissionStatus.DRAFT:

            # if we have from_date and number is empty
            if (from_date := self.cleaned_data.get('from_date')) and self.cleaned_data.get('number', None) is None:
                self.cleaned_data['number'] = self.calculate_number()
            else:
                if self.cleaned_data.get('number', None) is None:
                    self.add_error(
                        'number',
                        ValidationError('Number requires from_Date to be autocalculated', code='invalid'))

            # set a title if empty
            if not self.cleaned_data.get('title') and (city := self.cleaned_data.get('city')):
                city = city.name.lower()
                self.cleaned_data['title'] = f"{self.cleaned_data['number']}-{self.cleaned_data['year']}_{city}"

        if 'status' in self.changed_data and self.instance:
            if (self.cleaned_data['status'] != Mission.MissionStatus.SUBMITTED and
                    self.instance.expenses.filter(reimbursement__isnull=False).exists()):
                raise ValidationError(
                    f'You cannot set to {self.cleaned_data["status"]} a mission with reimbursed exception')

        return ret

    class Meta:
        model = Mission
        fields = '__all__'


class ExpenseAdminForm(forms.ModelForm):

    def clean(self):
        ret = super().clean()

        if not self.cleaned_data.get('currency') and (mission := self.cleaned_data['mission']):
            self.cleaned_data['currency'] = mission.default_currency

        return ret

    class Meta:
        model = Expense
        fields = '__all__'


class MissionsImportForm(forms.Form):
    """Accepts .zip missions dump to import."""

    file = forms.FileField(help_text='Load the missions zip file')

    def is_valid(self):
        ret = super().is_valid()
        if ret:
            MissionImporter(self.cleaned_data['file']).validate()
        return ret


class MissionsReimbursementForm(forms.Form):
    """Form for reimbursement of multiple expenses."""
    expenses = forms.CharField(widget=forms.HiddenInput())
    year = forms.IntegerField(help_text='Please select the fiscal year for the reimbursements', required=True)
    title = forms.CharField(help_text='The mission name will be [resource]-[year]-[title]', required=True)

    def get_initial_for_field(self, field, field_name):
        if field_name == 'title':
            return datetime.date.today().strftime('%B')
        return super().get_initial_for_field(field, field_name)

    def clean(self):
        ret = super().clean()
        ReimbursementFacility(self.cleaned_data['expenses']).check_year(self.cleaned_data['year'])
        return ret


class ReimbursementAdminForm(forms.ModelForm):

    def calculate_number(self) -> int:
        return Reimbursement.calculate_number(self.instance and self.instance.id, self.cleaned_data['year'])

    def get_initial_for_field(self, field, field_name):
        if field_name == 'year':
            return datetime.date.today().year
        return super().get_initial_for_field(field, field_name)

    def clean_number(self):
        number = self.cleaned_data['number']
        if number and number <= 0:
            raise ValidationError('Number must be > 0')

    def clean(self):
        """Clean data."""
        ret = super().clean()
        if self.cleaned_data.get('number', None) is None:
            self.cleaned_data['number'] = self.calculate_number()

        return ret

    class Meta:
        model = Mission
        fields = '__all__'
