from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from krm3.missions.api.serializers.expense import ExpenseSerializer
from krm3.missions.models import DocumentType, Expense, ExpenseCategory, PaymentCategory

BASE_JSON = {
    'mission': 1,
    'day': '2023-11-23',
    'payment_type': {
        'id': 1,
        '__str__': 'CC',
        'title': 'CC',
        'active': True,
        'parent': None
    },
    'document_type': {
        'id': 3,
        'title': 'Fattura',
        'active': True,
        'default': False
    },
    'category': {
        'id': 9,
        '__str__': 'Varie:Rappresentanza',
        'title': 'Rappresentanza',
        'active': True,
        'parent': 7
    },
    'amount_currency': '10',
    'amount_base': ''
}


def test_api_create_mission(expense, admin_user):
    assert Expense.objects.count() == 1
    num_payment_categories = PaymentCategory.objects.count()
    num_doc_type = DocumentType.objects.count()
    num_Expense_category = ExpenseCategory.objects.count()

    expense.id = None
    expense.detail = 'copy'
    exp = ExpenseSerializer(expense)
    client = APIClient()
    client.force_authenticate(user=admin_user)
    url = reverse('missions:expense-list')
    response = client.post(url, data=exp.data, format='json')

    assert response
    assert Expense.objects.count() == 2
    assert num_payment_categories == PaymentCategory.objects.count()
    assert num_doc_type == DocumentType.objects.count()
    assert num_Expense_category == ExpenseCategory.objects.count()
