from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from krm3.currencies.models import Currency
from krm3.missions.api.serializers.expense import ExpenseCreateSerializer
from krm3.core.models import DocumentType, Expense, ExpenseCategory, Mission, PaymentCategory, Reimbursement

BASE_JSON = {
    'mission': 1,
    'day': '2023-11-23',
    'payment_type': {'id': 1, '__str__': 'CC', 'title': 'CC', 'active': True, 'parent': None},
    'document_type': {'id': 3, 'title': 'Fattura', 'active': True, 'default': False},
    'category': {'id': 9, '__str__': 'Varie:Rappresentanza', 'title': 'Rappresentanza', 'active': True, 'parent': 7},
    'amount_currency': '10',
}


def test_api_create_mission(expense, admin_user):
    assert Expense.objects.count() == 1

    fks = {
        'category': ExpenseCategory,
        'document_type': DocumentType,
        'payment_type': PaymentCategory,
        'currency': Currency,
        'mission': Mission,
        'reimbursement': Reimbursement,
    }

    counters = {fk: cls.objects.count() for fk, cls in fks.items()}

    expdata = dict(ExpenseCreateSerializer(expense).data)
    expdata['detail'] = 'copy'

    serializer = ExpenseCreateSerializer(data=expdata)
    validated = serializer.is_valid(raise_exception=False)
    assert validated is True

    client = APIClient()
    client.force_authenticate(user=admin_user)
    url = reverse('missions-api:expense-list')
    response = client.post(url, data=expdata, format='json')

    assert response.status_code == 201
    response_data = dict(response.data)
    assert response_data == {
        'mission': expense.mission_id,
        'day': expense.day.strftime('%Y-%m-%d'),
        'amount_currency': str(expense.amount_currency),
        'currency': expense.currency_id,
        'detail': 'copy',
        'category': expense.category_id,
        'document_type': expense.document_type_id,
        'payment_type': expense.payment_type_id,
        'image': expdata['image'],
    }
    assert Expense.objects.count() == 2
    assert counters == {fk: cls.objects.count() for fk, cls in fks.items()}
