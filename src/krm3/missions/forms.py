from django.core.exceptions import ValidationError
from django.db.models import Max
from django.forms import ModelForm

from krm3.missions.models import Mission


class MissionAdminForm(ModelForm):

    def clean(self):
        ret = super().clean()

        if (from_date := self.cleaned_data['from_date']) and not self.cleaned_data['number']:
            qs = Mission.objects.filter(from_date__year=from_date.year)
            if self.instance.id:
                qs = qs.exclude(pk=self.instance.id)
            number = qs.aggregate(Max('number'))['number__max'] or 0
            self.cleaned_data['number'] = number + 1
        else:
            if not self.cleaned_data['number']:
                self.add_error('number', ValidationError('Number requires from_Date to be autocalculated',
                                                         code='invalid'))

        return ret

    class Meta:
        model = Mission
        fields = '__all__'
