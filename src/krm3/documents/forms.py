from __future__ import annotations

import io
import typing

from pypdf import PdfWriter
from django import forms
from django.core.files.uploadedfile import UploadedFile
from django.utils.translation import gettext_lazy as _l
from krm3.core.models.documents import ProtectedDocument as Document

from krm3.core.models import Resource
from krm3.documents.importers import dms_registry
from krm3.utils.pdf import extract_text, pdf_page_iterator


class PayslipImportForm(forms.Form):
    """Import payslip file."""

    basename = forms.CharField(help_text=_l('Base filename'))
    file = forms.FileField(help_text=_l('Load the payslip file.'))
    importer = forms.ChoiceField(choices=list)

    @typing.override
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.fields['importer'].choices = [[k, k] for k, _ in dms_registry.items()]
        self.resources = {r.fiscal_code: r for r in Resource.objects.filter(fiscal_code__isnull=False)}
        self._documents = {}

    def find_resource(self, text: str) -> Resource | None:
        for cf, res in self.resources.items():
            if cf in text:
                return res
        return None

    def is_valid(self) -> bool:
        """Extract documents from payslip file.

        Return true if the payslips were found.
        """
        return super().is_valid() and self._do_import_documents()

    def _do_import_documents(self) -> bool:
        """Load the payslips extracted in the form.is_valid."""
        for page in pdf_page_iterator(self.cleaned_data['file']):
            text = extract_text(page)

            resource = self.find_resource(text)

            if resource:
                writer = self._documents.setdefault(resource, PdfWriter())
                writer.add_page(page)

        if bool(self._documents):
            for resource, writer in self._documents.items():
                content = io.BytesIO()
                writer.write(content)
                content.seek(0)
                docname = (
                    f'{self.cleaned_data["basename"]}-{resource.last_name.title()}{resource.first_name.title()}.pdf'
                )
                Document.add(UploadedFile(content, docname), actor=None, admin=resource.user, tags=['payslip.monthly'])
                content.close()
            return True
        return False
