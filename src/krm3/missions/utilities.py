import decimal
from decimal import Decimal

from django.db.models import QuerySet

from krm3.core.models import ExpenseCategory, Expense, Reimbursement


def calculate_reimbursement_summaries(qs: QuerySet[Expense]) -> tuple[dict, dict, dict]:
    bypayment = {'Company': [decimal.Decimal('0.0')] * 3, 'Personal': [decimal.Decimal('0.0')] * 3}
    byexpcategory = {pc: [decimal.Decimal('0.0')] * 4 for pc in ExpenseCategory.objects.root_nodes()}
    summary = {
        Reimbursement.ReimbursementSummaryEnum.TOTALE_SPESE: decimal.Decimal('0.0'),
        Reimbursement.ReimbursementSummaryEnum.TOTALE_RIMBORSO: decimal.Decimal('0.0'),
        Reimbursement.ReimbursementSummaryEnum.NON_RIMBORSATE: decimal.Decimal('0.0'),
        Reimbursement.ReimbursementSummaryEnum.DA_RESTITUIRE: decimal.Decimal('0.0'),
    } | {expense.category.get_root(): decimal.Decimal('0.0') for expense in qs}
    for expense in qs:
        expense: Expense
        exp_cat_root = expense.category.get_root()
        base, reimbursement = expense.amount_base or Decimal('0.0'), expense.amount_reimbursement or Decimal('0.0')

        summary[Reimbursement.ReimbursementSummaryEnum.TOTALE_RIMBORSO] += reimbursement

        byexpcategory[exp_cat_root][0] += base
        byexpcategory[exp_cat_root][1] += reimbursement

        if expense.payment_type.personal_expense:
            key = 'Personal'
            summary[exp_cat_root] += reimbursement
            summary[Reimbursement.ReimbursementSummaryEnum.NON_RIMBORSATE] += base - reimbursement

            byexpcategory[exp_cat_root][2] += base - reimbursement
            byexpcategory[exp_cat_root][3] += reimbursement
            bypayment[key][2] += base - reimbursement
            summary[Reimbursement.ReimbursementSummaryEnum.TOTALE_SPESE] += reimbursement
            bypayment[key][1] += reimbursement
        else:
            key = 'Company'
            summary[exp_cat_root] += base + reimbursement
            summary[Reimbursement.ReimbursementSummaryEnum.DA_RESTITUIRE] -= reimbursement
            byexpcategory[exp_cat_root][2] -= reimbursement
            byexpcategory[exp_cat_root][3] += base + reimbursement
            bypayment[key][2] += base + reimbursement
            summary[Reimbursement.ReimbursementSummaryEnum.TOTALE_SPESE] += base + reimbursement
            bypayment[key][1] -= reimbursement

        bypayment[key][0] += base

    return byexpcategory, bypayment, summary
