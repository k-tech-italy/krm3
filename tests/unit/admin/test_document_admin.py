import typing
from pathlib import Path

import pytest
from django.urls import reverse
from django_webtest import DjangoTestApp
from testutils.factories import DocumentFactory, DocumentTagFactory, ResourceFactory, SuperUserFactory
from webtest import Upload

from krm3.documents.admin import Krm3DocumentAdmin
from krm3.documents.importers import KTPayslipImporter

if typing.TYPE_CHECKING:
    from django_webtest.pytest_plugin import MixinWithInstanceVariables


@pytest.fixture(autouse=True)
def models_cleanup(self_cleaning_add):
    return


@pytest.fixture
def app(django_app_factory: 'MixinWithInstanceVariables') -> DjangoTestApp:
    django_app = django_app_factory(csrf_checks=False)
    admin_user = SuperUserFactory(username='superuser')
    django_app.set_user(admin_user)
    django_app._user = admin_user
    return django_app


@pytest.fixture
def resources():
    DocumentTagFactory(title='payslip.monthly')
    return [
        ResourceFactory(fiscal_code='PLNPRN95B01F839O'),
        ResourceFactory(fiscal_code='ZIOPRN95B01H501U'),
        ResourceFactory(fiscal_code='NNNPRN73T24H501Y'),
        ResourceFactory(fiscal_code='DPPPCI80A01H501P'),
    ]


def test_file_upload_view(app, resources):
    from krm3.core.models import ProtectedDocument

    test_file = Path(__file__).parents[2] / 'examples' / 'KTPayslip_ANON.2022.pdf'

    response = app.get(reverse('admin:core_protecteddocument_import_payslips'))
    form = response.forms['payslip-upload-form']

    form['basename'] = 'BustaPaga'
    form['importer'] = KTPayslipImporter.name
    form['file'] = Upload('hello.pdf', test_file.read_bytes(), content_type='application/pdf')

    response = form.submit()
    assert response.status_code == 302
    response = response.follow()
    assert 'Successfully imported 4 payslips.' in response.text

    assert ProtectedDocument.objects.count() == 4
    tags = list(ProtectedDocument.objects.values_list('document2tag__tag__title', flat=True))
    assert tags == ['payslip.monthly'] * 4


def test_file_link_returns_html_link_when_document_has_file(db):
    """file_link should return an HTML link when the document has a file."""
    doc = DocumentFactory()  # DocumentFactory creates a document with a file
    admin_instance = Krm3DocumentAdmin(model=doc.__class__, admin_site=None)

    result = admin_instance.file_link(doc)

    expected_url = reverse('media-auth:document-file', args=[doc.pk])
    assert f'href="{expected_url}"' in result
    assert 'View file' in result


def test_file_link_returns_dash_when_document_has_no_file(db):
    """file_link should return '-' when the document has no file."""
    doc = DocumentFactory(document=None)  # No file attached
    admin_instance = Krm3DocumentAdmin(model=doc.__class__, admin_site=None)

    result = admin_instance.file_link(doc)

    assert result == '-'


def test_import_payslips_get_returns_form(app):
    """GET request to import_payslips should return the upload form."""
    response = app.get(reverse('admin:core_protecteddocument_import_payslips'))

    assert response.status_code == 200
    assert 'payslip-upload-form' in response.forms
    assert 'Import Payslips' in response.text


def test_import_payslips_post_with_no_matching_resources_shows_error(app):
    """POST with PDF that matches no resources should show error message."""
    from krm3.core.models import ProtectedDocument

    # No resources with fiscal codes set up - the PDF won't match anyone
    test_file = Path(__file__).parents[2] / 'examples' / 'KTPayslip_ANON.2022.pdf'

    response = app.get(reverse('admin:core_protecteddocument_import_payslips'))
    form = response.forms['payslip-upload-form']

    form['basename'] = 'BustaPaga'
    form['importer'] = KTPayslipImporter.name
    form['file'] = Upload('hello.pdf', test_file.read_bytes(), content_type='application/pdf')

    response = form.submit()
    assert response.status_code == 302
    response = response.follow()
    assert 'Error. Found 0 payslips.' in response.text

    assert ProtectedDocument.objects.count() == 0
