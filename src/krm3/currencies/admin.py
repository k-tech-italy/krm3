from admin_extra_buttons.decorators import button
from admin_extra_buttons.mixins import ExtraButtonsMixin, confirm_action
from django.contrib import admin
from django.contrib.admin import ModelAdmin

from krm3.currencies.models import Currency, Rate


@admin.register(Currency)
class CurrencyAdmin(ModelAdmin):
    list_display = ('iso3', 'symbol', 'title', 'active')
    search_fields = ('iso3', 'title')
    list_filter = ('active', )


@admin.register(Rate)
class RateAdmin(ExtraButtonsMixin, ModelAdmin):
    list_display = ['day', 'rates']
    list_filter = ('day',)

    @button(html_attrs={'style': 'background-color:#DC6C6C;color:black'})
    def refresh(self, request, pk):
        def _action(req):
            rate = Rate.objects.get(pk=pk)
            rate.get_rates(force=True)

        return confirm_action(self, request, _action, 'Confirm refresh rates from online service',
                              'Successfully refreshed', )
