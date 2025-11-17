from django.utils.translation import gettext_lazy as _l
from django_simple_dms.admin import DocumentAdmin
from django_simple_dms.models import Document
from django.contrib.admin import site

class Krm3DocumentAdmin(DocumentAdmin):
    class Meta:
        verbose_name = _l('Document')
        verbose_name_plural = _l('Documents')

site.unregister(Document)
site.register(Document, Krm3DocumentAdmin)
