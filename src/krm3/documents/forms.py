from django import forms
from django.utils.translation import gettext_lazy as _l


class PayslipImportForm(forms.Form):
    """Import payslip file."""

    file = forms.FileField(help_text=_l('Load the payslip file.'))
    importer = forms.ChoiceField(choices=list)

    # def __init__(self, data=None, files=None, auto_id="id_%s", prefix=None, initial=None, error_class=...,
    #              label_suffix=None, empty_permitted=False, field_order=None, use_required_attribute=None,
    #              renderer=None):
    #     super().__init__(data, files, auto_id, prefix, initial, error_class, label_suffix, empty_permitted, field_order,
    #                      use_required_attribute, renderer)

    def is_valid(self) -> bool:
        ret = super().is_valid()
        # if ret:
        #     MissionImporter(self.cleaned_data['file']).validate()
        return ret
