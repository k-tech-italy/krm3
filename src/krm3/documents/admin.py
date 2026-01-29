from __future__ import annotations

import typing

from admin_extra_buttons.decorators import button
from admin_extra_buttons.mixins import ExtraButtonsMixin
from django.contrib import admin, messages
from django.contrib.admin import site
from django.contrib.admin.templatetags.admin_urls import admin_urlname
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _l
from django_simple_dms.admin import DocumentAdmin
from django_simple_dms.models import Document

from krm3.core.forms import ProtectedDocumentForm
from krm3.core.models import ProtectedDocument
from krm3.styles.buttons import DANGEROUS

from .forms import PayslipImportForm

if typing.TYPE_CHECKING:
    from django.http import HttpRequest


class Krm3DocumentAdmin(ExtraButtonsMixin, DocumentAdmin):
    """Custom admin for ProtectedDocument with private media support and payslip import."""

    form = ProtectedDocumentForm
    list_display = ['__str__', 'admin', 'upload_date', 'file_link']
    readonly_fields = ['file_link']

    @admin.display(description='File')
    def file_link(self, obj: ProtectedDocument) -> str:
        if obj.file_url:
            return format_html('<a href="{}">View file</a>', obj.file_url)
        return '-'

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
            # Use self.model._meta to get correct URL for ProtectedDocument
            return redirect(admin_urlname(self.model._meta, 'changelist'))

        form = PayslipImportForm()
        context['form'] = form
        return TemplateResponse(request, 'admin/documents/payslip_upload.html', context)


site.unregister(Document)
site.register(ProtectedDocument, Krm3DocumentAdmin)
