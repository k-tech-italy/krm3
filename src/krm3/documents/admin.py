from __future__ import annotations

import typing

from admin_extra_buttons.decorators import button
from admin_extra_buttons.mixins import ExtraButtonsMixin
from django.contrib import messages
from django.contrib.admin import site
from django.contrib.admin.templatetags.admin_urls import admin_urlname
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.utils.translation import gettext_lazy as _l
from django_simple_dms.admin import DocumentAdmin
from django_simple_dms.models import Document

from krm3.styles.buttons import DANGEROUS

from .forms import PayslipImportForm

if typing.TYPE_CHECKING:
    from django.http import HttpRequest

class Krm3DocumentAdmin(ExtraButtonsMixin, DocumentAdmin):
    @button(html_attrs=DANGEROUS)
    def import_payslips(self, request: HttpRequest) -> None:
        context = self.get_common_context(request, title=_l('Import Payslips'))
        if request.method == 'POST':
            form = PayslipImportForm(request.POST, request.FILES)
            if form.is_valid():
                messages.success(
                    request, _l('Successfully imported {num} payslips.').format(num=len(form._documents))
                )
            else:
                messages.error(request, _l('Error. Found {num} payslips.').format(num=len(form._documents)))
            return redirect(admin_urlname(context['opts'], 'changelist'))

        form = PayslipImportForm()
        context['form'] = form
        return TemplateResponse(request, 'admin/documents/payslip_upload.html', context)


site.unregister(Document)
site.register(Document, Krm3DocumentAdmin)
