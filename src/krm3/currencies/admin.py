from admin_extra_buttons.decorators import button
from admin_extra_buttons.mixins import ExtraButtonsMixin, confirm_action
from django.contrib import admin
from django.contrib.admin import ModelAdmin
from django.template.response import TemplateResponse

from krm3.currencies.forms import RatesImportForm
from krm3.currencies.impexp import RateImporter
from krm3.currencies.models import Currency, Rate
from krm3.styles.buttons import NORMAL


@admin.register(Currency)
class CurrencyAdmin(ModelAdmin):
    list_display = ('iso3', 'symbol', 'title', 'active')
    search_fields = ('iso3', 'title')
    list_filter = ('active', )


@admin.register(Rate)
class RateAdmin(ExtraButtonsMixin, ModelAdmin):
    list_display = ['day', 'rates']
    list_filter = ('day',)

    @button(html_attrs={'style': NORMAL})
    def refresh(self, request, pk):
        def _action(req):
            rate = Rate.objects.get(pk=pk)
            rate.get_rates(force=True)

        return confirm_action(self, request, _action, 'Confirm refresh rates from online service',
                              'Successfully refreshed', )

    @button(html_attrs=NORMAL)
    def import_rates(self, request):  # noqa: D102
        if request.method == 'POST':
            form = RatesImportForm(request.POST, request.FILES)
            if form.is_valid():
                rate_importer = RateImporter(request)
                return self._return_preview(rate_importer, request)
        else:
            sorting = request.GET.get('sort')
            rate_importer = RateImporter(request, from_session=True)
            return self._return_preview(rate_importer, request, sorting)

    @staticmethod
    def _return_preview(rate_importer, request, sorting=None):
        data = rate_importer.preview(sorting=sorting)
        return TemplateResponse(
            request,
            context={
                'data': data
            }, template='admin/currencies/import_rates_check.html'
        )
