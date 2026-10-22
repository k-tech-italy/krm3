import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from factory.fuzzy import FuzzyChoice
from testutils.factories import ExpenseFactory, MissionFactory

from krm3.core.models import Expense
from krm3.currencies.models import Currency


@pytest.fixture
def euro_currency():
    Currency.objects.get(iso3='EUR')


@pytest.fixture
def mission(euro_currency):
    return MissionFactory()


@pytest.fixture
def expense(categories, payment_types, document_types):
    return ExpenseFactory(
        category=FuzzyChoice(categories.expenses.values()),
        payment_type=FuzzyChoice(categories.payments.values()),
        document_type=FuzzyChoice(document_types),
    )


@pytest.fixture
def private_media(tmp_path, monkeypatch):
    """Store the private media files (e.g. expense images) in a temporary directory."""
    storage = Expense._meta.get_field('image').storage
    monkeypatch.setattr(storage, 'base_location', str(tmp_path), raising=False)
    monkeypatch.setattr(storage, 'location', str(tmp_path), raising=False)
    return tmp_path


@pytest.fixture
def expense_image():
    return SimpleUploadedFile('receipt.pdf', b'%PDF-1.4 receipt', content_type='application/pdf')
