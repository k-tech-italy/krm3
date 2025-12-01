from __future__ import annotations

import io
import typing

from PyPDF2 import PdfWriter
from django import forms
from django.core.files.uploadedfile import UploadedFile
from django.utils.translation import gettext_lazy as _l
from django_simple_dms.models import Document

from krm3.core.models import Resource
from krm3.documents.importers import dms_registry
from krm3.utils.pdf import extract_text, pdf_page_iterator

class PayslipImportForm(forms.Form):
    """Import payslip file."""

    basename = forms.CharField(help_text=_l('Base filename'))
    file = forms.FileField(help_text=_l('Load the payslip file.'))
    importer = forms.ChoiceField(choices=list)

    def __init__(self, *args: typing.ParamSpecArgs, **kwargs: typing.ParamSpecArgs) -> None:
        super().__init__(*args, **kwargs)
        self.fields['importer'].choices = [[k, k] for k, _ in dms_registry.items()]
        self.resources = {r.fiscal_code: r for r in Resource.objects.filter(fiscal_code__isnull=False)}

    def find_resource(self, text: str) -> Resource | None:
        for cf, res in self.resources.items():
            if f'CodicesFiscale\n{cf}' in text:
                return res
        return None

    def is_valid(self) -> bool:
        ret = super().is_valid()
        resources_found = []

        if ret:
            documents = {}
            for page in pdf_page_iterator(self.cleaned_data['file']):
                text = extract_text(page)

                resource = self.find_resource(text)

                if resource:
                    writer = documents.setdefault(resource, PdfWriter())
                    writer.add_page(page)

            for resource, writer in documents.items():
                content = io.BytesIO()
                writer.write(content)
                resources_found.append(resource)
                content.seek(0)
                docname = (
                    f'{self.cleaned_data["basename"]}-{resource.last_name.title()}{resource.first_name.title()}.pdf'
                )
                Document.add(UploadedFile(content, docname), actor=None, admin=resource.user, tags=['payslip.monthly'])

        self._resources_found = resources_found
        if not resources_found:
            return False

        return ret
