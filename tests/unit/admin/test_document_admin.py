import typing
from pathlib import Path

import pytest
from django.urls import reverse
from django_webtest import DjangoTestApp
from testutils.factories import DocumentTagFactory, ResourceFactory, SuperUserFactory
from webtest import Upload

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
    from django_simple_dms.models import Document

    test_file = Path(__file__).parents[2] / 'examples' / 'KTPayslip_ANON.2022.pdf'

    response = app.get(reverse('admin:django_simple_dms_document_import_payslips'))
    form = response.forms['payslip-upload-form']

    form['basename'] = 'BustaPaga'
    form['importer'] = KTPayslipImporter.name
    form['file'] = Upload('hello.pdf', test_file.read_bytes(), content_type='application/pdf')

    response = form.submit()
    assert response.status_code == 302
    response = response.follow()
    assert 'Successfully imported 4 payslips.' in response.text

    assert Document.objects.count() == 4
    tags = list(Document.objects.values_list('document2tag__tag__title', flat=True))
    assert tags == ['payslip.monthly'] * 4
