import datetime

from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.text import slugify

from krm3.currencies.models import Currency
from krm3.missions.facilities import ReimbursementFacility
from krm3.missions.impexp.imp import MissionImporter
from krm3.core.models import Expense, Mission, Reimbursement


class MissionAdminForm(forms.ModelForm):
    def calculate_number(self) -> int:
        return Mission.calculate_number(self.instance and self.instance.id, self.cleaned_data['year'])

    def clean_number(self):
        number = self.cleaned_data['number']
        if number and number <= 0:
            raise ValidationError('Number must be > 0')
        return number

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
                        'number', ValidationError('Number requires from_date to be autocalculated', code='invalid')
                    )

            # set a title if empty
            self.cleaned_data['title'] = Mission.calculate_title(self.cleaned_data)

        if 'status' in self.changed_data and self.instance:
            if (
                    self.cleaned_data['status'] != Mission.MissionStatus.SUBMITTED
                    and self.instance.expenses.filter(reimbursement__isnull=False).exists()
            ):
                raise ValidationError(
                    f'You cannot set to {self.cleaned_data["status"]} a mission with reimbursed exception'
                )

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
    year = forms.IntegerField(help_text='Please select the fiscal year for the reimbursements', required=True,
                              initial=lambda: datetime.date.today().year)
    month = forms.CharField(help_text='Month of reimbursement', required=True,
                            initial=lambda: datetime.date.today().strftime('%b'))
    title = forms.CharField(help_text='If blank calculated as R_[year]_[num:3]_[mmm]_[last_name]', required=False)

    def clean(self):
        ret = super().clean()
        ReimbursementFacility(self.cleaned_data['expenses']).check_year(self.cleaned_data['year'])
        return ret


class ReimbursementAdminForm(forms.ModelForm):
    title = forms.CharField(
        required=False, widget=forms.TextInput(attrs={'size': 60}), help_text='Set automatically if left blank'
    )

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
        model = Reimbursement
        fields = '__all__'
