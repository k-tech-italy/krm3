from krm3.currencies.models import Rate


def update_rates(qs):
    rates_dict = {}
    for expense in qs:
        rate = rates_dict.setdefault(expense.day, Rate.for_date(expense.day))
        expense.amount_base = rate.convert(expense.amount_currency, from_currency=expense.currency)
        if expense.amount_reimbursement is None:
            expense.amount_reimbursement = expense.get_reimbursement_amount()
        expense.save()
