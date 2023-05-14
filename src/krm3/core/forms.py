from django.core.exceptions import ValidationError
from django.forms import ModelForm


class ResourceAdminForm(ModelForm):

    def clean(self):
        ret = super().clean()
        msg = ' isMandatory if you do not specify profile'

        if profile := self.cleaned_data['profile']:
            self.cleaned_data['first_name'] = profile.user.first_name
            self.cleaned_data['last_name'] = profile.user.last_name
        else:
            if not self.cleaned_data['first_name']:
                self.add_error('first_name', ValidationError(f'First name{msg}', code='invalid'))
            if not self.cleaned_data['last_name']:
                self.add_error('last_name', ValidationError(f'Last name{msg}', code='invalid'))

        return ret
