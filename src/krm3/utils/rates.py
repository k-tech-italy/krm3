import typing

from pyoxr import OXRError

from krm3.currencies.models import Rate
from krm3.missions.exceptions import RateConversionError

if typing.TYPE_CHECKING:
    from django.db.models import QuerySet

    from krm3.core.models import Expense


def update_rates(qs: 'QuerySet[Expense]') -> None:
    rates_dict = {}
    try:
        for expense in qs:
            if expense.day not in rates_dict:
                rates_dict[expense.day] = Rate.for_date(expense.day)
            rate = rates_dict[expense.day]
            expense.amount_base = rate.convert(expense.amount_currency, from_currency=expense.currency)
            if expense.amount_reimbursement is None:
                expense.amount_reimbursement = expense.get_reimbursement_amount()
            expense.save()
    except OXRError as e:
        raise RateConversionError(e)
