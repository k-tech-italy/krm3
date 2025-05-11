import decimal
from decimal import Decimal

from django.db.models import QuerySet

from krm3.core.models import ExpenseCategory, Expense


def calculate_reimbursement_summaries(qs: QuerySet[Expense]) -> tuple[dict, dict, dict]:
    bypayment = {'Company': [decimal.Decimal('0.0')] * 2, 'Personal': [decimal.Decimal('0.0')] * 2}
    byexpcategory = {pc: [decimal.Decimal('0.0')] * 2 for pc in ExpenseCategory.objects.root_nodes()}
    summary = {
        'Totale spese': decimal.Decimal('0.0'),
        'Totale rimborso': decimal.Decimal('0.0'),
        'Non Rimborsate': decimal.Decimal('0.0'),
    } | {expense.category.get_root(): decimal.Decimal('0.0') for expense in qs}
    for expense in qs:
        expense: Expense
        summary['Totale rimborso'] += expense.amount_reimbursement or decimal.Decimal('0.0')
        summary[expense.category.get_root()] += expense.amount_reimbursement or decimal.Decimal('0.0')

        key = 'Personal' if expense.payment_type.personal_expense else 'Company'
        bypayment[key][0] += expense.amount_base or Decimal('0.0')
        bypayment[key][1] += expense.amount_reimbursement or Decimal('0.0')

        byexpcategory[expense.category.get_root()][0] += expense.amount_base or Decimal('0')
        byexpcategory[expense.category.get_root()][1] += expense.amount_reimbursement or Decimal('0')
        summary['Non Rimborsate'] += (
            (expense.amount_base or decimal.Decimal('0.0')) - (expense.amount_reimbursement or decimal.Decimal('0.0'))
            if expense.payment_type.personal_expense
            else decimal.Decimal('0.0')
        )
        summary['Totale spese'] += (
            expense.amount_base
            if not expense.payment_type.personal_expense
            else expense.amount_reimbursement or Decimal('0.0')
        ) or decimal.Decimal('0.0')
    return byexpcategory, bypayment, summary
