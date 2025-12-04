from admin_extra_buttons.decorators import button
from admin_extra_buttons.mixins import ExtraButtonsMixin
from django.contrib.admin.templatetags.admin_urls import admin_urlname
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.utils.translation import gettext_lazy as _l
from django_simple_dms.admin import DocumentAdmin
from django_simple_dms.models import Document
from django.contrib.admin import site

from .forms import PayslipImportForm
from krm3.styles.buttons import DANGEROUS


class Krm3DocumentAdmin(ExtraButtonsMixin, DocumentAdmin):
    @button(html_attrs=DANGEROUS)
    def import_payslips(self, request: 'HttpRequest') -> None:
        context = self.get_common_context(request, title=_l('Import Payslips'))
        if request.method == 'POST':
            form = PayslipImportForm(request.POST, request.FILES)
            if form.is_valid():
                downloaded_file = request.FILES['docfile']
                # process file
                ...
                ...
                return redirect(admin_urlname(context['opts'], 'changelist'))
        else:
            form = PayslipImportForm()
        context['form'] = form
        return TemplateResponse(request, 'admin/documents/payslip_upload.html', context)

        # if request.method == 'POST':
        #     form = MissionsImportForm(request.POST, request.FILES)
        #     if form.is_valid():
        #         target = MissionImporter(request.FILES['file']).store()
        #         data = MissionImporter.get_data(target)
        #         data = json.dumps(data, indent=4)
        #
        #         return TemplateResponse(
        #             request, context={'data': data}, template='admin/missions/mission/import_missions_check.html'
        #         )
        #     return None
        # form = MissionsImportForm()
        # return TemplateResponse(request, context={'form': form}, template='admin/missions/mission/import_missions.html')


site.unregister(Document)
site.register(Document, Krm3DocumentAdmin)
